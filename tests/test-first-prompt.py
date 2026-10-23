#!/usr/bin/env python3
"""Check that the very first prompt of an interactive zsh is powerlevel10k's.

A unit test cannot catch the bug this guards against: it is an ordering bug, and
powerlevel10k silently skips the first paint when it is sourced before the
user's `compinit`. The theme then only appears from the second prompt, which is
why this test drives a real PTY the way T3 does and reads the bytes before any
input is typed.
"""

import argparse
import fcntl
import os
import pty
import select
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import termios
import time
import urllib.request

BLOCK_MARKER = "# t3-vibecoding prompt block"
THEME_PATH = "/usr/share/powerlevel10k/powerlevel10k.zsh-theme"
PROMPT_GLYPH = "\u276f"  # powerlevel10k's prompt character with the lean style.


def write_file(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def download_theme(version: str, destination: str) -> str:
    url = f"https://github.com/romkatv/powerlevel10k/archive/refs/tags/{version}.tar.gz"
    archive = os.path.join(destination, "p10k.tar.gz")
    with urllib.request.urlopen(url) as response, open(archive, "wb") as handle:
        shutil.copyfileobj(response, handle)
    root = os.path.join(destination, "p10k")
    os.makedirs(root)
    with tarfile.open(archive) as tar:
        tar.extractall(root, filter="data")
    return os.path.join(root, os.listdir(root)[0])


def build_home(theme_dir: str, block_path: str) -> str:
    home = tempfile.mkdtemp(prefix="p10k-first-prompt-")
    with open(block_path, encoding="utf-8") as handle:
        block = handle.read().replace(
            THEME_PATH, os.path.join(theme_dir, "powerlevel10k.zsh-theme")
        )
    # Mirrors the .zshrc Debian's newuser installer writes, which is what most
    # users end up with. The block is appended after it, exactly as
    # startup_prepare_shell does, so the test fails if the theme runs before
    # `compinit` or if another prompt wins at the end of the file.
    zshrc = (
        "autoload -Uz promptinit\n"
        "promptinit\n"
        "prompt adam1\n"
        "autoload -Uz compinit\n"
        # -i ignores insecure fpath directories: on a hosted runner /usr/local
        # is writable by the invoking user, so a bare compinit asks a question
        # and the prompt is never painted. The ordering the test cares about is
        # unchanged: the theme still has to be sourced after compinit.
        "compinit -i\n"
        "[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh\n" + block
    )
    write_file(os.path.join(home, ".zshrc"), zshrc)
    with open(os.path.join(theme_dir, "config", "p10k-lean.zsh"), encoding="utf-8") as handle:
        config = handle.read()
    # gitstatusd is fetched over the network on first use: disable it so the
    # test does not depend on GitHub being reachable from the prompt.
    write_file(
        os.path.join(home, ".p10k.zsh"),
        config + "\nPOWERLEVEL9K_DISABLE_GITSTATUS=true\n",
    )
    return home


def first_prompt(home: str, seconds: float) -> str:
    pid, fd = pty.fork()
    if pid == 0:
        os.environ.update(
            HOME=home,
            XDG_CACHE_HOME=os.path.join(home, ".cache"),
            TERM="xterm-256color",
        )
        # -d skips the machine's global rc files: this test is about the user
        # rc the add-on writes. On the image the system rc only sets up
        # completion and history, which tests/test-startup.sh covers.
        os.execvp("zsh", ["zsh", "-d", "-o", "nopromptsp"])
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 120, 0, 0))
    output = b""
    deadline = time.time() + seconds
    while time.time() < deadline:
        ready, _, _ = select.select([fd], [], [], 0.2)
        if not ready:
            continue
        try:
            chunk = os.read(fd, 65536)
        except OSError:
            break
        if not chunk:
            break
        output += chunk
        if PROMPT_GLYPH.encode() in output:
            break
    shutdown(fd, pid)
    return output.decode("utf-8", "replace")


def shutdown(fd: int, pid: int) -> None:
    try:
        os.write(fd, b"exit\n")
        os.close(fd)
    except OSError:
        pass
    deadline = time.time() + 5
    while time.time() < deadline:
        exited, _ = os.waitpid(pid, os.WNOHANG)
        if exited == pid:
            return
        time.sleep(0.05)
    os.kill(pid, 9)
    os.waitpid(pid, 0)


def compaudit_report() -> str:
    """List the fpath entries that make compinit ask for confirmation."""
    try:
        result = subprocess.run(
            ["zsh", "-fc", "autoload -Uz compaudit && compaudit"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return (result.stdout + result.stderr).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p10k-version", required=True)
    parser.add_argument(
        "--block",
        default=os.path.join(
            os.path.dirname(__file__), "..", "t3_vibecoding", "zshrc-block"
        ),
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    block_path = os.path.abspath(args.block)
    with open(block_path, encoding="utf-8") as handle:
        if BLOCK_MARKER not in handle.read():
            print(f"FAIL: {block_path} is not the managed prompt block", file=sys.stderr)
            return 1

    with tempfile.TemporaryDirectory(prefix="p10k-download-") as download_dir:
        theme_dir = download_theme(args.p10k_version, download_dir)
        home = build_home(theme_dir, block_path)
        try:
            prompt = first_prompt(home, args.timeout)
        finally:
            shutil.rmtree(home, ignore_errors=True)

    if PROMPT_GLYPH not in prompt:
        print("FAIL: the first prompt is not powerlevel10k's", file=sys.stderr)
        print(f"captured: {prompt!r}", file=sys.stderr)
        audit = compaudit_report()
        if audit:
            print(f"compaudit reports insecure fpath directories:\n{audit}", file=sys.stderr)
        return 1

    print("ok first prompt is powerlevel10k's")
    return 0


if __name__ == "__main__":
    sys.exit(main())
