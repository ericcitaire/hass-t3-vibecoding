#!/usr/bin/env python3
"""Fail a pull request that changes user-visible files without a CHANGELOG entry.

A change is user-visible when it touches one of ``USER_VISIBLE_PATHS``. Such a
pull request must add at least one bullet to the ``## Unreleased`` section of
``t3_vibecoding/CHANGELOG.md``. Documentation-, CI- and test-only pull requests
are exempt; the ``skip-changelog`` label opts an internal change out explicitly.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import addon_versions

USER_VISIBLE_PATHS = (
    "t3_vibecoding/Dockerfile",
    "t3_vibecoding/run.sh",
    "t3_vibecoding/lib/",
    "t3_vibecoding/services/",
    "t3_vibecoding/config.yaml",
    "t3_vibecoding/translations/",
    "t3_vibecoding/browser-packages.txt",
    "t3_vibecoding/zshrc",
    "t3_vibecoding/zshrc-block",
    "t3_vibecoding/icon.png",
)


def user_visible(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in USER_VISIBLE_PATHS)


def changed_files(base: str, root: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", f"{base}...HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in completed.stdout.splitlines() if line]


def base_changelog(base: str, root: Path) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(root), "show", f"{base}:{addon_versions.CHANGELOG}"],
        capture_output=True,
        text=True,
    )
    return completed.stdout if completed.returncode == 0 else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="base commit of the pull request")
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--skip",
        action="store_true",
        help="opt out (used for the skip-changelog label)",
    )
    args = parser.parse_args(argv)

    if args.skip:
        print("CHANGELOG gate skipped.")
        return 0

    root = Path(args.root).resolve()
    try:
        touched = changed_files(args.base, root)
    except subprocess.CalledProcessError as error:
        print(f"could not diff against {args.base}: {error}", file=sys.stderr)
        return 2

    if not any(user_visible(path) for path in touched):
        print("No user-visible path changed; no CHANGELOG entry required.")
        return 0

    head = (root / addon_versions.CHANGELOG).read_text(encoding="utf-8")
    base = base_changelog(args.base, root)
    added = len(addon_versions.unreleased_bullets(head)) - (
        len(addon_versions.unreleased_bullets(base)) if base else 0
    )
    if added <= 0:
        print(
            "This pull request changes a user-visible path but adds no bullet to",
            "`## Unreleased` in t3_vibecoding/CHANGELOG.md.",
            "Add one under `### Added`, `### Changed` or `### Fixed`, or apply the",
            "`skip-changelog` label when the change is internal.",
        )
        return 1

    print(f"CHANGELOG entry OK: {added} new Unreleased bullet(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
