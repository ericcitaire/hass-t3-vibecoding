#!/usr/bin/env python3
"""Tests for the PDF tooling check."""

from __future__ import annotations

import sys
import unittest
from importlib import util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

_spec = util.spec_from_file_location("verify_pdf_packages", SCRIPTS / "verify-pdf-packages.py")
assert _spec and _spec.loader
pdf = util.module_from_spec(_spec)
_spec.loader.exec_module(pdf)


class PdfPackagesTest(unittest.TestCase):
    def test_the_repository_installs_the_stack(self):
        packages = pdf.installed_packages((ROOT / "t3_vibecoding" / "Dockerfile").read_text(encoding="utf-8"))
        self.assertEqual(pdf.missing_packages(packages), [])

    def test_a_missing_package_is_reported(self):
        dockerfile = (
            "RUN apt-get update \\\n"
            " && apt-get install -y --no-install-recommends \\\n"
            "      poppler-utils python3-pil \\\n"
            " && rm -rf /var/lib/apt/lists/*\n"
        )
        packages = pdf.installed_packages(dockerfile)
        self.assertEqual(
            pdf.missing_packages(packages), ["python3-pymupdf", "python3-reportlab"]
        )

    def test_continuation_lines_and_other_layers_are_parsed(self):
        dockerfile = (
            "RUN apt-get install -y --no-install-recommends \\\n"
            "      nodejs \\\n"
            " && npm install -g t3\n"
            "RUN apt-get install -y --no-install-recommends gh\n"
            "RUN apt-get install -y --no-install-recommends poppler-utils \\\n"
            "      python3-pil python3-pymupdf python3-reportlab\n"
        )
        packages = pdf.installed_packages(dockerfile)
        self.assertIn("nodejs", packages)
        self.assertIn("gh", packages)
        self.assertEqual(pdf.missing_packages(packages), [])


if __name__ == "__main__":
    unittest.main()
