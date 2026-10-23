#!/usr/bin/env python3
"""Compare the pinned components with upstream and assemble the release PR.

Subcommands:

    detect   print what upstream publishes, next to what the image pins
    prepare  rewrite the release surfaces and emit the PR payload as JSON

The weekly GitHub Actions workflow runs ``prepare``: when a component moved it
bumps the build args, `version` in config.yaml, the CHANGELOG entry and the
DOCS.md quotes in a single commit, verifies the result, and opens the release
PR. Nothing is pushed from here; the workflow does that.

Logs go to stderr so that stdout stays valid JSON.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path

import addon_versions as versions

USER_AGENT = "hass-t3-vibecoding-dependency-sweep/1"
BRANCH = "chore/dependency-sweep"
BASE_IMAGE_REPOSITORY = "home-assistant/docker-base"
BASE_IMAGE_TAG = re.compile(r"^\d{4}\.\d{2}\.\d+$")


class FetchError(RuntimeError):
    """An upstream index could not be read."""


def log(message: str) -> None:
    print(message, file=sys.stderr)


# --------------------------------------------------------------- upstream


def fetch_json(url: str, token: str | None = None, attempts: int = 3) -> object:
    """GET a JSON document, retrying transient failures."""

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if "api.github.com" in url:
        headers["Accept"] = "application/vnd.github+json"
        if token:
            headers["Authorization"] = f"Bearer {token}"

    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2 * (attempt + 1))
    raise FetchError(f"could not read {url}: {last_error}")


def npm_latest(package: str, token: str | None = None) -> str:
    """Latest stable version: the ``latest`` dist-tag, never preview/nightly."""

    url = f"https://registry.npmjs.org/{urllib.parse.quote(package, safe='@')}/latest"
    document = fetch_json(url, token)
    if not isinstance(document, dict) or "version" not in document:
        raise FetchError(f"unexpected npm document for {package}")
    return str(document["version"])


def github_latest_tag(repository: str, token: str | None = None) -> str:
    """Highest semantic-version tag of a GitHub repository."""

    url = f"https://api.github.com/repos/{repository}/tags?per_page=100"
    document = fetch_json(url, token)
    if not isinstance(document, list):
        raise FetchError(f"unexpected GitHub tags document for {repository}")

    tags: list[tuple[tuple[int, int, int], str]] = []
    for entry in document:
        name = str(entry.get("name", "")) if isinstance(entry, dict) else ""
        try:
            tags.append((versions.parse_version(name), name))
        except ValueError:
            continue
    if not tags:
        raise FetchError(f"no semantic-version tag found for {repository}")
    return max(tags)[1]


def latest_for(component: versions.Component, token: str | None = None) -> str:
    if component.datasource == "npm":
        return npm_latest(component.package, token)
    if component.datasource == "github-tags":
        return github_latest_tag(component.package, token)
    raise FetchError(f"unknown datasource {component.datasource!r}")


def base_image(token: str | None = None) -> dict[str, str | None]:
    """Informational: the base image alias floats, so it never forces a bump."""

    try:
        document = fetch_json(
            f"https://api.github.com/repos/{BASE_IMAGE_REPOSITORY}/tags?per_page=100",
            token,
        )
    except FetchError as error:
        log(f"warning: base image lookup skipped ({error})")
        return {"repository": BASE_IMAGE_REPOSITORY, "latest_tag": None}

    latest: tuple[tuple[int, int, int], str] | None = None
    if isinstance(document, list):
        for entry in document:
            name = str(entry.get("name", "")) if isinstance(entry, dict) else ""
            if not BASE_IMAGE_TAG.match(name):
                continue
            candidate = tuple(int(part) for part in name.split("."))
            if latest is None or candidate > latest[0]:
                latest = (candidate, name)
    return {
        "repository": BASE_IMAGE_REPOSITORY,
        "latest_tag": latest[1] if latest else None,
    }


# ------------------------------------------------------------------ sweep


def measure(
    dockerfile: str, resolve: Callable[[versions.Component], str]
) -> list[dict[str, str]]:
    """Compare each pinned component with what upstream publishes."""

    pinned = versions.read_args(dockerfile)
    rows: list[dict[str, str]] = []
    for component in versions.COMPONENTS:
        current = pinned.get(component.arg)
        if current is None:
            raise SystemExit(f"{versions.DOCKERFILE}: ARG {component.arg} is missing")
        latest = resolve(component)
        rows.append(
            {
                "key": component.key,
                "label": component.label,
                "arg": component.arg,
                "current": current,
                "latest": latest,
                "bump": versions.classify_bump(current, latest),
            }
        )
    return rows


def last_release_epoch(root: Path) -> int | None:
    """When the add-on version last moved, according to git."""

    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "log", "-1", "--format=%ct", "--", versions.CONFIG],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = completed.stdout.strip()
    return int(value) if value.isdigit() else None


def render_table(rows: list[dict[str, str]]) -> str:
    width = max(len(row["label"]) for row in rows)
    lines = [f"{'component'.ljust(width)}  {'pinned':<10}  {'latest':<10}  bump"]
    for row in rows:
        lines.append(
            f"{row['label'].ljust(width)}  {row['current']:<10}  "
            f"{row['latest']:<10}  {row['bump']}"
        )
    return "\n".join(lines)


def release_notes(rows: list[dict[str, str]]) -> list[str]:
    notes = []
    for row in rows:
        component = next(c for c in versions.COMPONENTS if c.key == row["key"])
        notes.append(
            f"- [{row['label']} {row['latest']}]({component.url(row['current'], row['latest'])})"
        )
    return notes


def build_pr_body(
    *,
    rows: list[dict[str, str]],
    drifted: list[dict[str, str]],
    version: str,
    image: str,
) -> str:
    lines = [
        "Automated **dependency sweep**: the versions pinned in the image compared",
        "with the versions published upstream.",
        "",
    ]
    if drifted:
        lines += ["| Component | Pinned | Latest | Bump |", "| --- | --- | --- | --- |"]
        for row in rows:
            lines.append(
                f"| {row['label']} | {row['current']} | {row['latest']} | {row['bump']} |"
            )
        lines += ["", "Release notes:", ""]
        lines += release_notes(drifted)
        unchanged = [row for row in rows if row["bump"] == "none"]
        if unchanged:
            lines += [
                "",
                "Unchanged: "
                + ", ".join(f"{row['label']} {row['current']}" for row in unchanged)
                + ".",
            ]
    else:
        lines += [
            "No bundled component moved. This is the **monthly package refresh**: it",
            "rebuilds the image on its floating `trixie` base so that upstream system",
            "and security fixes reach users.",
        ]

    lines += [
        "",
        f"This PR bumps `version` to **{version}**, prepends the `CHANGELOG.md` entry",
        "and keeps the versions quoted in `DOCS.md` in sync, so the four release",
        "surfaces stay coherent.",
        "",
        f"Merging it publishes `{image}:{version}`: the add-on version is the image",
        "tag the Supervisor pulls.",
        "",
        "Generated by `scripts/dependency-sweep.py`.",
    ]
    return "\n".join(lines)


def commit_message(version: str, drifted: list[dict[str, str]]) -> str:
    if not drifted:
        return f"chore(addon): release {version} (package refresh)"
    names = []
    for row in drifted:
        component = next(c for c in versions.COMPONENTS if c.key == row["key"])
        names.append(f"{component.short} {row['latest']}")
    return f"chore(addon): release {version} with " + " and ".join(names)


def nothing_to_do(reason: str, rows: list[dict[str, str]], **extra: object) -> dict[str, object]:
    return {"prepared": False, "reason": reason, "components": rows, **extra}


def prepare(
    root: Path,
    *,
    force: bool,
    guard_days: int | None,
    resolve: Callable[[versions.Component], str],
    dry_run: bool,
    now: int | None = None,
    resolve_base: Callable[[], dict[str, str | None]] | None = None,
) -> dict[str, object]:
    """Rewrite the release surfaces; return the PR payload."""

    surfaces = versions.read_surfaces(root)
    rows = measure(surfaces[versions.DOCKERFILE], resolve)
    drifted = [row for row in rows if row["bump"] != "none"]

    if not drifted and not force:
        return nothing_to_do("no upstream release since the pinned version", rows)

    if force and guard_days is not None:
        epoch = last_release_epoch(root)
        if epoch is not None:
            age = (now if now is not None else int(time.time())) - epoch
            if age < guard_days * 86400:
                return nothing_to_do(
                    f"a release was published less than {guard_days} days ago",
                    rows,
                )
        else:
            log("warning: recent-release guard skipped (no git history)")

    kind = "minor" if any(row["bump"] == "minor" for row in drifted) else "patch"
    current_version = versions.read_config_version(surfaces[versions.CONFIG])
    version = versions.next_version(current_version, kind)

    dockerfile = surfaces[versions.DOCKERFILE]
    docs = surfaces[versions.DOCS]
    for row in drifted:
        component = next(c for c in versions.COMPONENTS if c.key == row["key"])
        dockerfile = versions.write_arg(dockerfile, component.arg, row["latest"])
        docs = versions.rewrite_docs_versions(
            docs, component, row["current"], row["latest"]
        )

    bullets = [
        versions.release_bullet(
            next(c for c in versions.COMPONENTS if c.key == row["key"]),
            row["current"],
            row["latest"],
        )
        for row in drifted
    ] or [versions.REFRESH_BULLET]

    files = {
        versions.DOCKERFILE: dockerfile,
        versions.CONFIG: versions.write_config_version(surfaces[versions.CONFIG], version),
        versions.CHANGELOG: versions.prepend_entry(
            surfaces[versions.CHANGELOG], version, bullets
        ),
        versions.DOCS: docs,
    }

    errors = versions.check_files(files)
    if errors:
        raise SystemExit(
            "release metadata would be inconsistent:\n  - " + "\n  - ".join(errors)
        )

    changed = sorted(path for path, text in files.items() if text != surfaces[path])
    if not dry_run:
        for path in changed:
            (root / path).write_text(files[path], encoding="utf-8")

    image = versions.read_image(files[versions.CONFIG])
    message = commit_message(version, drifted)
    log(render_table(rows))
    log(f"\nrelease {current_version} -> {version} ({kind}); changed: {', '.join(changed)}")

    return {
        "prepared": True,
        "dry_run": dry_run,
        "version": version,
        "previous_version": current_version,
        "kind": kind,
        "branch": BRANCH,
        "commit_message": message,
        "pr_title": message,
        "pr_body": build_pr_body(
            rows=rows, drifted=drifted, version=version, image=image
        ),
        "components": rows,
        "drift": [row["key"] for row in drifted],
        "changed_files": changed,
        "base_image": resolve_base() if resolve_base is not None else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("detect", "prepare"))
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--force",
        action="store_true",
        help="publish a patch release even when nothing drifted",
    )
    parser.add_argument(
        "--recent-release-guard-days",
        type=int,
        help="with --force, stand down when a release landed less than N days ago",
    )
    parser.add_argument("--dry-run", action="store_true", help="write nothing")
    parser.add_argument(
        "--github-token", default=os.environ.get("SWEEP_GITHUB_TOKEN") or None
    )
    parser.add_argument(
        "--base-image",
        action="store_true",
        help="also resolve the floating base image (informational, needs network)",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    def resolve(component: versions.Component) -> str:
        return latest_for(component, args.github_token)

    if args.command == "detect":
        surfaces = versions.read_surfaces(root)
        rows = measure(surfaces[versions.DOCKERFILE], resolve)
        payload: dict[str, object] = {
            "components": rows,
            "drifted": [row["key"] for row in rows if row["bump"] != "none"],
            "addon_version": versions.read_config_version(surfaces[versions.CONFIG]),
        }
        if args.base_image:
            payload["base_image"] = base_image(args.github_token)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            log(render_table(rows))
        return 0

    payload = prepare(
        root,
        force=args.force,
        guard_days=args.recent_release_guard_days,
        resolve=resolve,
        dry_run=args.dry_run,
        resolve_base=lambda: base_image(args.github_token),
    )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
