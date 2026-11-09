#!/usr/bin/env python3
"""Check that the add-on image still ships the PDF tooling agents rely on.

Agents read real documents (scanned meeting minutes, statements) and need both
a fast text extractor and a page renderer. The image installs them as Debian
packages because its Python is externally managed: `pip install` requires
`--break-system-packages`, which is the trap this check keeps out of the image.

Run locally in the add-on container or from a checkout:
    python3 scripts/verify-pdf-packages.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = ROOT / "t3_vibecoding" / "Dockerfile"

# Package name -> what it brings to the image.
REQUIRED = {
    "poppler-utils": "pdftotext, pdfinfo, pdftoppm and pdfimages",
    "python3-pil": "Pillow (PIL) for saving rendered pages",
    "python3-pymupdf": "PyMuPDF for text extraction and page rendering",
    "python3-reportlab": "ReportLab for generating PDFs",
}

INSTALL = re.compile(r"apt-get\s+install\b(?P<args>.*?)(?:&&|\Z)", re.DOTALL)
TOKEN = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")


def installed_packages(text: str) -> set[str]:
    """Return every package named by an `apt-get install` command in a Dockerfile."""

    packages: set[str] = set()
    for match in INSTALL.finditer(text):
        args = match.group("args").replace("\\", " ")
        for token in re.split(r"\s+", args):
            if TOKEN.match(token):
                packages.add(token)
    return packages


def missing_packages(packages: set[str]) -> list[str]:
    return [name for name in REQUIRED if name not in packages]


def main() -> int:
    packages = installed_packages(DOCKERFILE.read_text(encoding="utf-8"))
    missing = missing_packages(packages)
    if missing:
        print("PDF tooling check failed:", file=sys.stderr)
        for name in missing:
            print(
                f"  - {name} is not installed by apt-get in "
                f"{DOCKERFILE.relative_to(ROOT)} ({REQUIRED[name]})",
                file=sys.stderr,
            )
        return 1

    print(f"PDF tooling OK: {', '.join(REQUIRED)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
