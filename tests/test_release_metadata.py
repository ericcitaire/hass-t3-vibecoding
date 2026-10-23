#!/usr/bin/env python3
"""Tests for the release metadata helpers and the dependency sweep."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from importlib import util
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import addon_versions as versions


def load_sweep():
    """Import scripts/dependency-sweep.py, whose name is not importable."""

    spec = util.spec_from_file_location("dependency_sweep", SCRIPTS / "dependency-sweep.py")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sweep = load_sweep()

ROOT = Path(__file__).resolve().parent.parent


class VersionMathTest(unittest.TestCase):
    def test_parse_accepts_the_powerlevel10k_prefix(self):
        self.assertEqual(versions.parse_version("v1.20.0"), (1, 20, 0))
        self.assertEqual(versions.parse_version("2.1.3"), (2, 1, 3))

    def test_classify_bump_follows_the_upstream_kind(self):
        self.assertEqual(versions.classify_bump("2.1.3", "2.1.4"), "patch")
        self.assertEqual(versions.classify_bump("2.1.3", "2.2.0"), "minor")
        self.assertEqual(versions.classify_bump("0.1.0", "1.0.0"), "minor")
        self.assertEqual(versions.classify_bump("2.1.3", "2.1.3"), "none")
        self.assertEqual(versions.classify_bump("2.1.3", "2.1.2"), "none")

    def test_next_version_keeps_the_addon_scheme(self):
        self.assertEqual(versions.next_version("0.14.0", "minor"), "0.15.0")
        self.assertEqual(versions.next_version("0.14.0", "patch"), "0.14.1")
        self.assertEqual(versions.next_version("0.14.3", "patch"), "0.14.4")


class SurfacesTest(unittest.TestCase):
    def setUp(self):
        self.files = versions.read_surfaces(ROOT)

    def test_the_repository_is_coherent(self):
        self.assertEqual(versions.check_files(self.files), [])

    def test_config_must_match_the_top_changelog_entry(self):
        stale = dict(self.files)
        stale[versions.CONFIG] = versions.write_config_version(
            self.files[versions.CONFIG], "0.13.1"
        )
        errors = versions.check_files(stale)
        self.assertTrue(any("top CHANGELOG entry" in error for error in errors))

    def test_docs_must_quote_the_build_arg(self):
        stale = dict(self.files)
        stale[versions.DOCS] = self.files[versions.DOCS].replace(
            "`t3` 0.1.0", "`t3` 0.0.9"
        )
        errors = versions.check_files(stale)
        self.assertTrue(any("T3 Code quotes" in error for error in errors))

    def test_placeholders_block_a_release(self):
        dirty = dict(self.files)
        top = versions.changelog_versions(self.files[versions.CHANGELOG])[0]
        dirty[versions.CHANGELOG] = self.files[versions.CHANGELOG].replace(
            f"## {top}\n", f"## {top}\n\n- TODO describe the impact\n", 1
        )
        errors = versions.check_files(dirty)
        self.assertTrue(any("TODO" in error for error in errors))

    def test_changelog_must_decrease(self):
        broken = dict(self.files)
        broken[versions.CHANGELOG] = "# Changelog\n\n## 0.14.0\n\n- x\n\n## 0.15.0\n\n- y\n"
        errors = versions.check_files(broken)
        self.assertTrue(any("must decrease" in error for error in errors))

    def test_docs_rewrite_updates_every_quotation(self):
        component = next(c for c in versions.COMPONENTS if c.key == "powerlevel10k")
        rewritten = versions.rewrite_docs_versions(
            self.files[versions.DOCS], component, "v1.20.0", "v1.21.0"
        )
        self.assertNotIn("v1.20.0", rewritten)
        self.assertEqual(versions.docs_versions(rewritten)["powerlevel10k"], {"v1.21.0"})


class PrepareTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        shutil.copytree(ROOT / versions.ADDON_DIR, self.root / versions.ADDON_DIR)

    def tearDown(self):
        self.directory.cleanup()

    def resolve(self, latest: dict[str, str]):
        return lambda component: latest.get(component.key) or self.pinned(component)

    def pinned(self, component: versions.Component) -> str:
        return versions.read_args(read(versions.DOCKERFILE, self.root))[component.arg]

    def test_no_drift_prepares_nothing(self):
        payload = sweep.prepare(
            self.root,
            force=False,
            guard_days=None,
            resolve=self.resolve({}),
            dry_run=False,
        )
        self.assertFalse(payload["prepared"])
        self.assertEqual(
            read(versions.CONFIG, self.root), read(versions.CONFIG, ROOT)
        )

    def test_patch_drift_produces_one_coherent_release(self):
        current = versions.read_config_version(read(versions.CONFIG, self.root))
        payload = sweep.prepare(
            self.root,
            force=False,
            guard_days=None,
            resolve=self.resolve({"opencode": "2.1.4", "t3": "0.1.2"}),
            dry_run=False,
        )

        self.assertTrue(payload["prepared"])
        self.assertEqual(payload["kind"], "patch")
        self.assertEqual(payload["version"], versions.next_version(current, "patch"))
        self.assertEqual(payload["changed_files"], sorted(versions.SURFACES))

        files = versions.read_surfaces(self.root)
        self.assertEqual(versions.check_files(files), [])
        self.assertEqual(versions.read_args(files[versions.DOCKERFILE])["T3_VERSION"], "0.1.2")
        self.assertEqual(
            versions.read_config_version(files[versions.CONFIG]), payload["version"]
        )
        self.assertEqual(
            versions.changelog_versions(files[versions.CHANGELOG])[0], payload["version"]
        )
        self.assertEqual(
            versions.docs_versions(files[versions.DOCS])["opencode"], {"2.1.4"}
        )
        body = str(payload["pr_body"])
        self.assertIn("ghcr.io/ericcitaire/hass-t3-vibecoding", body)
        self.assertIn(str(payload["version"]), body)

    def test_minor_upstream_release_opens_a_minor_addon_release(self):
        payload = sweep.prepare(
            self.root,
            force=False,
            guard_days=None,
            resolve=self.resolve({"t3": "0.2.0"}),
            dry_run=False,
        )
        self.assertEqual(payload["kind"], "minor")
        self.assertTrue(str(payload["version"]).endswith(".0"))

    def test_force_refresh_without_drift_keeps_the_components(self):
        before = versions.read_args(read(versions.DOCKERFILE, self.root))
        payload = sweep.prepare(
            self.root,
            force=True,
            guard_days=None,
            resolve=self.resolve({}),
            dry_run=False,
        )
        self.assertTrue(payload["prepared"])
        self.assertIn("package refresh", str(payload["commit_message"]))
        self.assertEqual(
            versions.read_args(read(versions.DOCKERFILE, self.root)), before
        )
        files = versions.read_surfaces(self.root)
        self.assertEqual(versions.check_files(files), [])

    def test_guard_without_git_history_stays_permissive(self):
        payload = sweep.prepare(
            self.root,
            force=True,
            guard_days=7,
            resolve=self.resolve({}),
            dry_run=False,
            now=int(sweep.time.time()),
        )
        # The checkout has no git history for the copied tree, so the guard
        # cannot fire; this asserts the fallback stays permissive.
        self.assertTrue(payload["prepared"])

    def test_dry_run_writes_nothing(self):
        before = read(versions.CONFIG, self.root)
        payload = sweep.prepare(
            self.root,
            force=False,
            guard_days=None,
            resolve=self.resolve({"opencode": "2.1.4"}),
            dry_run=True,
        )
        self.assertTrue(payload["prepared"])
        self.assertEqual(read(versions.CONFIG, self.root), before)


class MeasureTest(unittest.TestCase):
    def test_measure_reports_drift_per_component(self):
        dockerfile = read(versions.DOCKERFILE, ROOT)
        rows = sweep.measure(dockerfile, lambda c: {"opencode": "2.1.4"}.get(c.key) or versions.read_args(dockerfile)[c.arg])
        bumps = {row["key"]: row["bump"] for row in rows}
        self.assertEqual(bumps["opencode"], "patch")
        self.assertEqual(bumps["t3"], "none")


def read(relative: str, root: Path) -> str:
    return (root / relative).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
