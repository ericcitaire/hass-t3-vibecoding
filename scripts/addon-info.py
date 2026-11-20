#!/usr/bin/env python3
"""Print one fact from an add-on release surface.

`scripts/addon_versions.py` owns what a release surface means; this module is
the shell's way in. GitHub Actions reads a version, the image name or one
Dockerfile build arg without growing a parser of its own:

    python3 scripts/addon-info.py version
    python3 scripts/addon-info.py image
    python3 scripts/addon-info.py arg T3_VERSION

``--from`` reads the surface from another path, which is how the build workflow
compares ``config.yaml`` with the commit before it. A missing surface or arg
prints the module's own message and exits 1.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import addon_versions

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, prog="addon-info.py")
    commands = parser.add_subparsers(dest="command", required=True)

    version = commands.add_parser("version", help="the add-on version in config.yaml")
    version.add_argument("--from", dest="source", type=Path, metavar="FILE")

    image = commands.add_parser("image", help="the image name in config.yaml")
    image.add_argument("--from", dest="source", type=Path, metavar="FILE")

    arg = commands.add_parser("arg", help="one ARG default in the Dockerfile")
    arg.add_argument("name", metavar="NAME")
    arg.add_argument("--from", dest="source", type=Path, metavar="FILE")

    args = parser.parse_args(argv)
    if args.command == "arg":
        surface = args.source or ROOT / addon_versions.DOCKERFILE
    else:
        surface = args.source or ROOT / addon_versions.CONFIG

    try:
        text = surface.read_text(encoding="utf-8")
        if args.command == "version":
            print(addon_versions.read_config_version(text))
        elif args.command == "image":
            print(addon_versions.read_image(text))
        else:
            print(addon_versions.read_arg(text, args.name))
    except (OSError, ValueError) as error:
        print(f"addon-info: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
