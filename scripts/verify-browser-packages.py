#!/usr/bin/env python3
"""Compare the add-on's browser packages with T3 Code's own list.

T3 embeds the Debian packages its headless preview browser needs in the
`DEBIAN_PACKAGES` constant of the `t3 browser setup` command. This script
extracts that list from a T3 binary and compares it with
`t3_vibecoding/browser-packages.txt`.

Run locally with a binary from the installed npm package:

    python3 scripts/verify-browser-packages.py --binary /path/to/t3

CI installs `t3@<T3_VERSION>` and passes the resolved binary.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import addon_versions

ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = ROOT / "t3_vibecoding" / "Dockerfile"
PACKAGES = ROOT / "t3_vibecoding" / "browser-packages.txt"

MARKER = b"DEBIAN_PACKAGES = ["
GROUP_LINE = re.compile(r'^\s*\[(?P<names>"[^"]+"(?:\s*,\s*"[^"]+")*)\]\s*,?\s*$')


def extract_groups(binary: Path) -> list[list[str]]:
    data = binary.read_bytes()
    offset = data.find(MARKER)
    if offset < 0:
        raise ValueError("DEBIAN_PACKAGES not found in the T3 binary")

    start = offset + len(MARKER)
    groups: list[list[str]] = []
    for line in data[start : start + 8192].decode("utf-8", "replace").splitlines():
        match = GROUP_LINE.match(line)
        if match is None:
            if groups:
                break
            if line.strip():
                break
            continue
        groups.append(re.findall(r'"([^"]+)"', match.group("names")))
    return groups


def read_packages(path: Path) -> list[str]:
    packages: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        name = line.strip()
        if name and not name.startswith("#"):
            packages.append(name)
    return packages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path, help="path to the t3 executable")
    parser.add_argument("--packages", type=Path, default=PACKAGES)
    args = parser.parse_args()

    try:
        version = addon_versions.read_arg(
            DOCKERFILE.read_text(encoding="utf-8"), "T3_VERSION"
        )
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    groups = extract_groups(args.binary)
    packages = read_packages(args.packages)
    if not groups:
        print("Could not extract DEBIAN_PACKAGES from the T3 binary.", file=sys.stderr)
        return 1

    errors: list[str] = []
    for group in groups:
        matches = [package for package in packages if package in group]
        if not matches:
            errors.append(f"missing a package for {group}")
        elif len(matches) > 1:
            errors.append(f"multiple packages for {group}: {matches}")

    known = {package for group in groups for package in group}
    for package in packages:
        if package not in known:
            errors.append(f"unexpected package not in T3's list: {package}")

    duplicates = sorted({package for package in packages if packages.count(package) > 1})
    for package in duplicates:
        errors.append(f"duplicate package: {package}")

    if errors:
        print(f"Browser packages do not match T3 {version}:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"Browser packages OK: {len(groups)} T3 groups covered (t3 {version}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
