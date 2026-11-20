#!/usr/bin/env python3
"""Tests for the release metadata helpers and the release workflow."""

from __future__ import annotations

import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from importlib import util
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import addon_versions as versions


def load_script(name: str):
    """Import a scripts/ entry point whose file name is not importable."""

    spec = util.spec_from_file_location(
        name.replace("-", "_"), SCRIPTS / f"{name}.py"
    )
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sweep = load_script("dependency-sweep")
gate = load_script("verify-changelog")
addon_info = load_script("addon-info")

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
        current = versions.read_config_version(self.files[versions.CONFIG])
        stale[versions.CONFIG] = versions.write_config_version(
            self.files[versions.CONFIG], versions.next_version(current, "patch")
        )
        errors = versions.check_files(stale)
        self.assertTrue(any("top CHANGELOG entry" in error for error in errors))

    def test_docs_must_quote_the_build_arg(self):
        component = next(c for c in versions.COMPONENTS if c.key == "t3")
        pinned = versions.read_args(self.files[versions.DOCKERFILE])["T3_VERSION"]
        stale = dict(self.files)
        stale[versions.DOCS] = versions.rewrite_docs_versions(
            self.files[versions.DOCS], component, pinned, "0.0.9"
        )
        self.assertNotEqual(stale[versions.DOCS], self.files[versions.DOCS])
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
        broken[versions.CHANGELOG] = (
            "# Changelog\n\n## Unreleased\n\n## 0.14.0\n\n- x\n\n## 0.15.0\n\n- y\n"
        )
        errors = versions.check_files(broken)
        self.assertTrue(any("must decrease" in error for error in errors))

    def test_docs_rewrite_updates_every_quotation(self):
        component = next(c for c in versions.COMPONENTS if c.key == "powerlevel10k")
        previous = versions.read_args(self.files[versions.DOCKERFILE])["POWERLEVEL10K_VERSION"]
        latest = "v" + versions.next_version(previous, "patch")
        rewritten = versions.rewrite_docs_versions(
            self.files[versions.DOCS], component, previous, latest
        )
        self.assertNotIn(previous, rewritten)
        self.assertEqual(versions.docs_versions(rewritten)["powerlevel10k"], {latest})


    def test_unreleased_is_the_first_entry(self):
        text = versions.replace_unreleased(
            self.files[versions.CHANGELOG],
            "### Added\n\n- A staged feature.",
        )
        top = versions.changelog_versions(text)[0]
        self.assertTrue(versions.has_unreleased(text))
        self.assertEqual(versions.unreleased_kind(text), "minor")
        self.assertLess(
            text.index("## Unreleased"), text.index(f"## {top}\n")
        )
        self.assertEqual(versions.check_unreleased(text), [])

    def test_missing_unreleased_is_an_error(self):
        changelog = self.files[versions.CHANGELOG]
        release = versions.next_version(
            versions.changelog_versions(changelog)[0], "minor"
        )
        broken = changelog.replace("## Unreleased\n", f"## {release}\n")
        errors = versions.check_unreleased(broken)
        self.assertTrue(any("no '## Unreleased'" in error for error in errors))

    def test_unreleased_sections_are_limited(self):
        text = versions.replace_unreleased(
            self.files[versions.CHANGELOG],
            "### Added\n\n- A feature.\n\n### Notes\n\n- Something else.",
        )
        errors = versions.check_unreleased(text)
        self.assertTrue(any("### Notes" in error for error in errors))

    def test_unreleased_placeholder_is_an_error(self):
        text = versions.replace_unreleased(
            self.files[versions.CHANGELOG], "### Fixed\n\n- TODO fix it."
        )
        errors = versions.check_unreleased(text)
        self.assertTrue(any("TODO" in error for error in errors))

    def test_unreleased_kind_follows_the_sections(self):
        changelog = self.files[versions.CHANGELOG]
        cases = {
            "### Added\n\n- x.": "minor",
            "### Changed\n\n- x.": "minor",
            "### Fixed\n\n- x.": "patch",
            "": None,
        }
        for body, expected in cases.items():
            with self.subTest(body=body):
                text = versions.replace_unreleased(changelog, body)
                self.assertEqual(versions.unreleased_kind(text), expected)

    def test_fold_keeps_human_sections_and_appends_components(self):
        changelog = self.files[versions.CHANGELOG]
        text = versions.replace_unreleased(
            changelog,
            "### Added\n\n- A feature.\n\n### Fixed\n\n- A fix.",
        )
        release = versions.next_version(
            versions.changelog_versions(changelog)[0], "minor"
        )
        folded = versions.fold_unreleased(
            text, release, ["- A bundled component."]
        )
        self.assertIn(f"## {release}", folded)
        self.assertIn("### Added\n\n- A feature.", folded)
        self.assertIn("### Fixed\n\n- A fix.", folded)
        self.assertIn("### Bundled components", folded)
        self.assertFalse(versions.has_unreleased(folded))
        self.assertEqual(versions.changelog_versions(folded)[0], release)
        self.assertEqual(versions.check_unreleased(folded), [])
        self.assertIn("A feature.", versions.top_entry(folded))


class PrepareTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        shutil.copytree(ROOT / versions.ADDON_DIR, self.root / versions.ADDON_DIR)
        self.empty_unreleased()

    def tearDown(self):
        self.directory.cleanup()

    def empty_unreleased(self):
        text = read(versions.CHANGELOG, self.root)
        write(versions.CHANGELOG, versions.replace_unreleased(text, ""), self.root)

    def resolve(self, latest: dict[str, str]):
        return lambda component: latest.get(component.key) or self.pinned(component)

    def pinned(self, component: versions.Component) -> str:
        return versions.read_args(read(versions.DOCKERFILE, self.root))[component.arg]

    def next_upstream(self, key: str, kind: str) -> str:
        """A version above the pinned one, so drift never depends on real releases."""

        component = next(c for c in versions.COMPONENTS if c.key == key)
        previous = self.pinned(component)
        bumped = versions.next_version(previous, kind)
        return f"v{bumped}" if previous.startswith("v") else bumped

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

    def test_unreleased_only_prepares_a_minor_release(self):
        current = versions.read_config_version(read(versions.CONFIG, self.root))
        text = read(versions.CHANGELOG, self.root)
        write(
            versions.CHANGELOG,
            versions.replace_unreleased(text, "### Added\n\n- Ship PDF tooling."),
            self.root,
        )
        payload = sweep.prepare(
            self.root,
            force=False,
            guard_days=None,
            resolve=self.resolve({}),
            dry_run=False,
        )

        self.assertTrue(payload["prepared"])
        self.assertEqual(payload["kind"], "minor")
        self.assertEqual(payload["version"], versions.next_version(current, "minor"))
        self.assertEqual(
            payload["changed_files"], sorted([versions.CONFIG, versions.CHANGELOG])
        )

        files = versions.read_surfaces(self.root)
        self.assertEqual(versions.check_files(files), [])
        self.assertIn("Ship PDF tooling", versions.top_entry(files[versions.CHANGELOG]))
        self.assertFalse(versions.has_unreleased(files[versions.CHANGELOG]))

    def test_invalid_unreleased_staging_fails_before_writing(self):
        text = read(versions.CHANGELOG, self.root)
        write(
            versions.CHANGELOG,
            versions.replace_unreleased(text, "### Notes\n\n- Something."),
            self.root,
        )
        with self.assertRaises(SystemExit) as caught:
            sweep.prepare(
                self.root,
                force=False,
                guard_days=None,
                resolve=self.resolve({}),
                dry_run=False,
            )
        self.assertIn("CHANGELOG staging", str(caught.exception))

    def test_unreleased_and_drift_share_one_release(self):
        text = read(versions.CHANGELOG, self.root)
        write(
            versions.CHANGELOG,
            versions.replace_unreleased(text, "### Fixed\n\n- Correct a thing."),
            self.root,
        )
        payload = sweep.prepare(
            self.root,
            force=False,
            guard_days=None,
            resolve=self.resolve({"opencode": self.next_upstream("opencode", "patch")}),
            dry_run=False,
        )

        self.assertTrue(payload["prepared"])
        self.assertEqual(payload["kind"], "patch")
        entry = versions.top_entry(versions.read_surfaces(self.root)[versions.CHANGELOG])
        self.assertIn("Correct a thing.", entry)
        self.assertIn("### Bundled components", entry)
        self.assertIn("Update `@opencode/cli`", entry)

    def test_patch_drift_produces_one_coherent_release(self):
        current = versions.read_config_version(read(versions.CONFIG, self.root))
        opencode = self.next_upstream("opencode", "patch")
        t3 = self.next_upstream("t3", "patch")
        payload = sweep.prepare(
            self.root,
            force=False,
            guard_days=None,
            resolve=self.resolve({"opencode": opencode, "t3": t3}),
            dry_run=False,
        )

        self.assertTrue(payload["prepared"])
        self.assertEqual(payload["kind"], "patch")
        self.assertEqual(payload["version"], versions.next_version(current, "patch"))
        self.assertEqual(payload["changed_files"], sorted(versions.SURFACES))

        files = versions.read_surfaces(self.root)
        self.assertEqual(versions.check_files(files), [])
        self.assertEqual(versions.read_args(files[versions.DOCKERFILE])["T3_VERSION"], t3)
        self.assertEqual(
            versions.read_config_version(files[versions.CONFIG]), payload["version"]
        )
        self.assertEqual(
            versions.changelog_versions(files[versions.CHANGELOG])[0], payload["version"]
        )
        self.assertEqual(
            versions.docs_versions(files[versions.DOCS])["opencode"], {opencode}
        )
        body = str(payload["pr_body"])
        self.assertIn("ghcr.io/ericcitaire/hass-t3-vibecoding", body)
        self.assertIn(str(payload["version"]), body)

    def test_minor_upstream_release_opens_a_minor_addon_release(self):
        payload = sweep.prepare(
            self.root,
            force=False,
            guard_days=None,
            resolve=self.resolve({"t3": self.next_upstream("t3", "minor")}),
            dry_run=False,
        )
        self.assertEqual(payload["kind"], "minor")
        self.assertTrue(str(payload["version"]).endswith(".0"))

    def test_force_release_without_drift_keeps_the_components(self):
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
            resolve=self.resolve({"opencode": self.next_upstream("opencode", "patch")}),
            dry_run=True,
        )
        self.assertTrue(payload["prepared"])
        self.assertEqual(read(versions.CONFIG, self.root), before)


class MeasureTest(unittest.TestCase):
    def test_measure_reports_drift_per_component(self):
        dockerfile = read(versions.DOCKERFILE, ROOT)
        pinned = versions.read_args(dockerfile)
        opencode = versions.next_version(pinned["OPENCODE_VERSION"], "patch")
        rows = sweep.measure(
            dockerfile,
            lambda component: opencode
            if component.key == "opencode"
            else pinned[component.arg],
        )
        bumps = {row["key"]: row["bump"] for row in rows}
        self.assertEqual(bumps["opencode"], "patch")
        self.assertEqual(bumps["t3"], "none")


class AddonInfoTest(unittest.TestCase):
    """The shell's way into the release surfaces."""

    def test_version_prints_the_addon_version(self):
        code, out, err = run_info("version")
        self.assertEqual(code, 0, err)
        self.assertEqual(
            out.strip(),
            versions.read_config_version(read(versions.CONFIG, ROOT)),
        )

    def test_image_prints_the_published_image(self):
        code, out, err = run_info("image")
        self.assertEqual(code, 0, err)
        self.assertEqual(
            out.strip(), versions.read_image(read(versions.CONFIG, ROOT))
        )

    def test_arg_prints_the_pinned_default(self):
        pinned = versions.read_args(read(versions.DOCKERFILE, ROOT))["T3_VERSION"]
        code, out, err = run_info("arg", "T3_VERSION")
        self.assertEqual(code, 0, err)
        self.assertEqual(out.strip(), pinned)

    def test_from_reads_another_surface(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            path.write_text('version: "9.9.9"\n', encoding="utf-8")
            code, out, err = run_info("version", "--from", str(path))
        self.assertEqual(code, 0, err)
        self.assertEqual(out.strip(), "9.9.9")

    def test_unknown_arg_fails_with_the_module_message(self):
        code, out, err = run_info("arg", "NOPE_VERSION")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("ARG NOPE_VERSION is missing", err)

    def test_unknown_command_is_a_usage_error(self):
        code, _, err = run_info("frobnicate")
        self.assertEqual(code, 2)
        self.assertIn("invalid choice", err)


class ChangelogGateTest(unittest.TestCase):
    def test_user_visible_paths(self):
        for path in (
            "t3_vibecoding/Dockerfile",
            "t3_vibecoding/run.sh",
            "t3_vibecoding/lib/startup.sh",
            "t3_vibecoding/services/t3/run",
            "t3_vibecoding/config.yaml",
            "t3_vibecoding/translations/en.yaml",
            "t3_vibecoding/browser-packages.txt",
            "t3_vibecoding/zshrc",
            "t3_vibecoding/zshrc-block",
            "t3_vibecoding/icon.png",
        ):
            self.assertTrue(gate.user_visible(path), path)
        for path in (
            "t3_vibecoding/DOCS.md",
            "t3_vibecoding/README.md",
            "t3_vibecoding/CHANGELOG.md",
            "README.md",
            "docs/adr/0007-release-notes.md",
            "tests/test_startup.sh",
            "scripts/verify-versions.py",
            ".github/workflows/verify.yml",
        ):
            self.assertFalse(gate.user_visible(path), path)

    def test_unreleased_bullets_only_count_staged_bullets(self):
        text = (
            "# Changelog\n\n## Unreleased\n\n### Added\n\n- one\n- two\n\n"
            "## 0.15.1\n\n- not counted\n"
        )
        self.assertEqual(len(versions.unreleased_bullets(text)), 2)

    def test_missing_unreleased_has_no_bullets(self):
        self.assertEqual(
            versions.unreleased_bullets("# Changelog\n\n## 0.15.1\n\n- one\n"), []
        )


def read(relative: str, root: Path) -> str:
    return (root / relative).read_text(encoding="utf-8")


def write(relative: str, text: str, root: Path) -> None:
    (root / relative).write_text(text, encoding="utf-8")


def run_info(*argv: str) -> tuple[int, str, str]:
    """Run the CLI in process, the way a shell caller would."""

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = addon_info.main(list(argv))
        except SystemExit as exit_error:  # argparse rejects an unknown command
            code = int(exit_error.code or 0)
    return code, out.getvalue(), err.getvalue()


if __name__ == "__main__":
    unittest.main()
