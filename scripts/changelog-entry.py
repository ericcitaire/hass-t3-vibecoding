#!/usr/bin/env python3
"""Print the CHANGELOG body of the currently released add-on version.

The build workflow uses this to fill the GitHub Release body, so the release
notes and the CHANGELOG entry cannot drift. The version in `config.yaml` and the
top CHANGELOG entry must agree; `verify-versions.py` enforces that on every
pull request.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import addon_versions


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    files = addon_versions.read_surfaces(root)
    version = addon_versions.read_config_version(files[addon_versions.CONFIG])
    releases = addon_versions.changelog_versions(files[addon_versions.CHANGELOG])
    if not releases or releases[0] != version:
        print(
            f"{addon_versions.CHANGELOG}: the top entry is not {version}",
            file=sys.stderr,
        )
        return 1

    body = addon_versions.top_entry(files[addon_versions.CHANGELOG]).strip()
    if not body:
        print(f"{addon_versions.CHANGELOG}: entry {version} is empty", file=sys.stderr)
        return 1
    print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
