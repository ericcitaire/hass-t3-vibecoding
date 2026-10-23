# Make zsh with powerlevel10k the integrated terminal's shell

Status: accepted

The add-on installed `zsh` next to `bash` but left the integrated terminal on
`bash`, so users had to know that `zsh` existed and start it by hand. 0.14.0
installs [powerlevel10k](https://github.com/romkatv/powerlevel10k) and makes
`zsh` the shell T3 opens, so the terminal is pleasant by default while staying
a plain, framework-free shell.

Three constraints shaped the implementation:

- T3 chooses the PTY shell from `$SHELL`, falling back to `bash`; it does not
  read `/etc/passwd` for that. `startup.sh` therefore exports `SHELL=/bin/zsh`
  (and `usermod` keeps `/etc/passwd` consistent for `docker exec` and for the
  `PATH` hydration candidates).
- At startup T3 hydrates `PATH` by running `zsh -ilc` **without a TTY**. That is
  an *interactive* shell, so powerlevel10k would offer its configuration wizard
  inside a pipe on every server start. The managed block only loads the theme
  when `[[ -t 0 && -t 1 ]]`, which is true in the PTY and false in the
  hydration subprocess.
- The persistent `HOME` (`/data/home`) makes any file there user data. The
  theme lives in `/usr/share/powerlevel10k`, unpacked from the pinned upstream
  tarball (no `.git`), and the add-on never writes or seeds `~/.p10k.zsh`: the
  wizard creates it on first use and the user owns it afterwards.

## Where the theme is sourced from

powerlevel10k is sourced by a small marked block that `startup_prepare_shell`
keeps at the **end** of `~/.zshrc`, not from the system-wide
`/etc/zsh/zshrc`. Two observed bugs forced that placement:

- Sourcing the theme before the user's `compinit` makes powerlevel10k skip the
  first paint. The shell then draws the prompt it had before (Debian's newuser
  template sets `prompt adam1`), and the p10k prompt only appears from the
  second prompt onwards. `/etc/zsh/zshrc` is read before `~/.zshrc`, so a theme
  sourced there always loses that ordering. Appending the block means it runs
  after whatever completion setup the user's rc performs, and the *first*
  prompt is p10k's.
- Without the instant-prompt cache that `p10k configure` writes near the top of
  `~/.zshrc`, p10k redirects its output and paints nothing at all, so a fresh
  home or a hand-written rc shows a blank prompt. The block therefore sets
  `POWERLEVEL9K_DISABLE_INSTANT_PROMPT=true` for that shell when
  `__p9k_instant_prompt_active` is unset, which takes the synchronous path and
  keeps the first prompt. When the cache exists, instant prompt stays enabled —
  the wizard's block runs before ours, which is the order p10k expects.

The block is idempotent: `startup_prepare_shell` returns early when the marker
is already present, appends a newline first when the file does not end with
one, and creates `~/.zshrc` containing only the block when the file is missing
(so Debian's newuser wizard does not run behind the user's back). `chown` puts
the file back under `dev`, since startup runs as root.

## Considered Options

- Keep `bash` by default and let users type `zsh`: rejected because the prompt
  styling is then invisible to anyone who does not already know it is there.
- `chsh -s /bin/zsh dev` alone: rejected because T3 ignores the login shell
  when it spawns the PTY.
- Ship Oh My Zsh on top of powerlevel10k: rejected because powerlevel10k runs
  standalone, and the extra framework adds startup output and behaviour the
  add-on would have to document without using.
- Seed `~/.zshrc` and `~/.p10k.zsh` on first boot: rejected because the home is
  persistent user data; a shipped theme would then either overwrite user edits
  or never receive fixes. The managed block is the exception: it is a few lines
  that carry no user settings and the add-on needs them to be present at a
  precise position.
- Source the theme from `/etc/zsh/zshrc`: rejected because that file is read
  before `~/.zshrc`; the theme then precedes the user's `compinit` and the first
  prompt is not p10k's (see above).
- Overwrite `/etc/zsh/zshrc` instead of appending: rejected because Debian's
  key bindings and sudo completion path live there.
- Pin a commit hash instead of the `v1.20.0` tag: rejected for legibility; the
  tag's commit is recorded next to the build arg if the tag ever moves.
- Install a Nerd Font in the image: rejected because glyphs are rendered by the
  client browser; a font in the image would only serve the headless preview
  browser. `DOCS.md` points at `fontFamilyTerminal` instead.

## Consequences

- The first zsh session shows powerlevel10k's configuration wizard; users who
  want no prompt customisation must answer it once, or answer `n` each time.
- The prompt's appearance depends on the client: without a Nerd Font, glyphs
  render as boxes until the user installs one or picks the wizard's ASCII mode.
- `PATH` hydration now runs through `zsh` rather than `bash`, so anything that
  only exists in `/etc/profile.d` still applies (Debian's `zprofile` sources
  it), but a broken `/etc/zsh/zshenv` would now affect server startup.
- `~/.zshrc` gains a marked block at its end. Users who edit the file keep it;
  users who delete the block get it back on the next start.
- The Debian `compinit` call is Ubuntu-only, so the system `/etc/zsh/zshrc`
  block initialises completion itself; a future Debian change may require
  revisiting that.
- `/usr/share/powerlevel10k` is owned by root and not writable by `dev`, so the
  optional `gitstatusd` helper is downloaded on first prompt into
  `/data/home/.cache/gitstatus` instead. Until then, git status is computed by
  the slower pure-zsh fallback.
- `tests/test-first-prompt.py` drives a real PTY and asserts the *first* prompt
  is p10k's, which is the only way to catch an ordering regression: with the
  theme sourced too early the second prompt looks correct.
