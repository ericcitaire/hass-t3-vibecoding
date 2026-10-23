#!/usr/bin/env python3
"""Release metadata truth for the add-on.

A released add-on version appears on four surfaces that must always agree:

* the ``ARG`` defaults in ``t3_vibecoding/Dockerfile`` (the bundled components);
* ``version`` in ``t3_vibecoding/config.yaml`` (which is also the image tag the
  Supervisor pulls);
* the top entry of ``t3_vibecoding/CHANGELOG.md``;
* the component versions quoted in ``t3_vibecoding/DOCS.md``.

``scripts/dependency-sweep.py`` rewrites those surfaces and
``scripts/verify-versions.py`` checks them; both go through this module so that
"coherent" has exactly one definition.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from textwrap import fill

ADDON_DIR = "t3_vibecoding"
DOCKERFILE = f"{ADDON_DIR}/Dockerfile"
CONFIG = f"{ADDON_DIR}/config.yaml"
CHANGELOG = f"{ADDON_DIR}/CHANGELOG.md"
DOCS = f"{ADDON_DIR}/DOCS.md"

SURFACES = (DOCKERFILE, CONFIG, CHANGELOG, DOCS)

_VERSION = r"v?\d+\.\d+\.\d+"
_VERSION_LINE = re.compile(r"^version:\s*\"(?P<version>[^\"]+)\"\s*$", re.MULTILINE)
_CHANGELOG_HEADING = re.compile(r"^## (?P<version>\d+\.\d+\.\d+)\s*$", re.MULTILINE)
_IMAGE = re.compile(r"^image:\s*\"(?P<image>[^\"]+)\"\s*$", re.MULTILINE)

PLACEHOLDERS = ("TODO", "FIXME", "TBD", "XXX")

WRAP = 80


@dataclass(frozen=True)
class Component:
    """One upstream project pinned in the image by a Dockerfile build arg."""

    key: str
    label: str
    short: str
    arg: str
    package: str
    datasource: str
    docs_patterns: tuple[str, ...]
    release_url: str

    def url(self, previous: str, latest: str) -> str:
        return self.release_url.format(
            package=self.package, previous=previous, latest=latest
        )


COMPONENTS: tuple[Component, ...] = (
    Component(
        key="opencode",
        label="OpenCode CLI",
        short="OpenCode",
        arg="OPENCODE_VERSION",
        package="@opencode/cli",
        datasource="npm",
        docs_patterns=(rf"`@opencode/cli` ({_VERSION})",),
        release_url="https://www.npmjs.com/package/{package}/v/{latest}",
    ),
    Component(
        key="t3",
        label="T3 Code",
        short="T3",
        arg="T3_VERSION",
        package="t3",
        datasource="npm",
        docs_patterns=(rf"`t3` ({_VERSION})",),
        release_url="https://www.npmjs.com/package/{package}/v/{latest}",
    ),
    Component(
        key="powerlevel10k",
        label="powerlevel10k",
        short="powerlevel10k",
        arg="POWERLEVEL10K_VERSION",
        package="romkatv/powerlevel10k",
        datasource="github-tags",
        docs_patterns=(
            rf"`powerlevel10k` ({_VERSION})",
            rf"powerlevel10k\]\(https://github\.com/romkatv/powerlevel10k\) ({_VERSION})",
        ),
        release_url="https://github.com/{package}/compare/{previous}...{latest}",
    ),
)


# ---------------------------------------------------------------- versions


def parse_version(value: str) -> tuple[int, int, int]:
    """Turn ``2.1.3`` or ``v1.20.0`` into a comparable tuple."""

    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", value.strip())
    if match is None:
        raise ValueError(f"not a semantic version: {value!r}")
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def classify_bump(current: str, latest: str) -> str:
    """Classify an upstream move as ``none``, ``patch`` or ``minor``.

    The add-on follows the same discipline as its history: an upstream major or
    minor release opens an add-on minor release, an upstream patch stays a
    patch.
    """

    previous_version = parse_version(current)
    latest_version = parse_version(latest)
    if latest_version <= previous_version:
        return "none"
    if latest_version[:2] != previous_version[:2]:
        return "minor"
    return "patch"


def next_version(current: str, kind: str) -> str:
    major, minor, patch = parse_version(current)
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    if kind == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"unknown release kind: {kind!r}")


# ------------------------------------------------------------- Dockerfile


def read_args(text: str) -> dict[str, str]:
    return dict(re.findall(r"^ARG ([A-Z0-9_]+)=(\S+)\s*$", text, re.MULTILINE))


def write_arg(text: str, name: str, value: str) -> str:
    pattern = rf"^ARG {re.escape(name)}=\S+\s*$"
    rewritten, count = re.subn(
        pattern, f"ARG {name}={value}", text, count=1, flags=re.MULTILINE
    )
    if count != 1:
        raise ValueError(f"{DOCKERFILE}: ARG {name} is missing")
    return rewritten


# -------------------------------------------------------------- config.yaml


def read_config_version(text: str) -> str:
    match = _VERSION_LINE.search(text)
    if match is None:
        raise ValueError(f"{CONFIG}: no 'version: \"x.y.z\"' line")
    return match.group("version")


def write_config_version(text: str, version: str) -> str:
    rewritten, count = _VERSION_LINE.subn(
        f'version: "{version}"', text, count=1
    )
    if count != 1:
        raise ValueError(f"{CONFIG}: no 'version: \"x.y.z\"' line")
    return rewritten


def read_image(text: str) -> str:
    match = _IMAGE.search(text)
    if match is None:
        raise ValueError(f"{CONFIG}: no 'image: \"...\"' line")
    return match.group("image")


# ------------------------------------------------------------------- DOCS


def docs_versions(text: str) -> dict[str, set[str]]:
    """Return the versions quoted in DOCS.md, per component key."""

    found: dict[str, set[str]] = {}
    for component in COMPONENTS:
        values: set[str] = set()
        for pattern in component.docs_patterns:
            values.update(match.group(1) for match in re.finditer(pattern, text))
        found[component.key] = values
    return found


def rewrite_docs_versions(text: str, component: Component, previous: str, latest: str) -> str:
    if previous == latest:
        return text
    for pattern in component.docs_patterns:
        text = re.sub(
            pattern,
            lambda match: match.group(0).replace(match.group(1), latest),
            text,
        )
    return text


# -------------------------------------------------------------- CHANGELOG


def changelog_versions(text: str) -> list[str]:
    return [match.group("version") for match in _CHANGELOG_HEADING.finditer(text)]


def top_entry(text: str) -> str:
    """Return the body of the first CHANGELOG entry."""

    headings = list(_CHANGELOG_HEADING.finditer(text))
    if not headings:
        raise ValueError(f"{CHANGELOG}: no '## <version>' entry found")
    start = headings[0].end()
    end = headings[1].start() if len(headings) > 1 else len(text)
    return text[start:end]


def format_entry(version: str, bullets: list[str]) -> str:
    lines = [f"## {version}", ""]
    for bullet in bullets:
        lines.append(
            fill(
                bullet,
                width=WRAP,
                subsequent_indent="  ",
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
    return "\n".join(lines)


def prepend_entry(text: str, version: str, bullets: list[str]) -> str:
    if not text.startswith("# Changelog"):
        raise ValueError(f"{CHANGELOG}: must start with '# Changelog'")
    rest = text[len("# Changelog") :].lstrip("\n")
    return f"# Changelog\n\n{format_entry(version, bullets)}\n\n{rest}"


def release_bullet(component: Component, previous: str, latest: str) -> str:
    return (
        f"- Update `{component.package}` from {previous} to **{latest}** "
        f"(the `{component.arg}` build arg default). "
        f"Release notes: {component.url(previous, latest)}"
    )


REFRESH_BULLET = (
    "- Refresh the image on its floating `trixie` base (Debian 13), picking up "
    "upstream system and security fixes. No bundled component changed."
)


# -------------------------------------------------------------- coherence


def read_surfaces(root: Path) -> dict[str, str]:
    return {path: (root / path).read_text(encoding="utf-8") for path in SURFACES}


def check_files(files: Mapping[str, str]) -> list[str]:
    """Return every incoherence between the release surfaces."""

    errors: list[str] = []

    try:
        config_version = read_config_version(files[CONFIG])
    except ValueError as error:
        return [str(error)]

    releases = changelog_versions(files[CHANGELOG])
    if not releases:
        errors.append(f"{CHANGELOG}: no '## <version>' entry found")
    else:
        if releases[0] != config_version:
            errors.append(
                f"{CONFIG} version {config_version} is not the top CHANGELOG "
                f"entry {releases[0]}"
            )
        for previous, current in itertools.pairwise(releases):
            if parse_version(current) >= parse_version(previous):
                errors.append(
                    f"{CHANGELOG}: entries must decrease, {previous} is followed "
                    f"by {current}"
                )
        entry = top_entry(files[CHANGELOG])
        if not entry.strip():
            errors.append(f"{CHANGELOG}: top entry {releases[0]} is empty")
        for placeholder in PLACEHOLDERS:
            if placeholder in entry:
                errors.append(
                    f"{CHANGELOG}: top entry {releases[0]} still contains the "
                    f"placeholder {placeholder}"
                )

    args = read_args(files[DOCKERFILE])
    quoted = docs_versions(files[DOCS])
    for component in COMPONENTS:
        pinned = args.get(component.arg)
        if pinned is None:
            errors.append(f"{DOCKERFILE}: ARG {component.arg} is missing")
            continue
        values = quoted[component.key]
        if not values:
            errors.append(f"{DOCS}: no version quoted for {component.label}")
        elif values != {pinned}:
            errors.append(
                f"{DOCS}: {component.label} quotes {sorted(values)} but "
                f"ARG {component.arg}={pinned}"
            )

    return errors


def check_root(root: Path) -> list[str]:
    return check_files(read_surfaces(root))
