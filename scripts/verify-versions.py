#!/usr/bin/env python3
"""Check that the add-on release surfaces still agree.

`version` in config.yaml, the top CHANGELOG.md entry, the versions quoted in
DOCS.md and the Dockerfile build arg defaults describe the same release. The
dependency sweep writes all four at once; this script fails the build when a
hand edit leaves them apart, when the CHANGELOG stops decreasing, or when a
placeholder survives into a releasable entry.

Run locally in the add-on container (python3 is installed):
    python3 scripts/verify-versions.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import addon_versions

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    errors = addon_versions.check_root(ROOT)
    if errors:
        print("Release metadata check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    files = addon_versions.read_surfaces(ROOT)
    version = addon_versions.read_config_version(files[addon_versions.CONFIG])
    components = ", ".join(component.label for component in addon_versions.COMPONENTS)
    print(f"Release metadata OK: {version} with {components}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
