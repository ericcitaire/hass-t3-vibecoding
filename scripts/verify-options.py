#!/usr/bin/env python3
"""Check that add-on option truth has not drifted.

The same option is declared in config.yaml, both translations, DOCS.md and
consumed in run.sh. This script verifies that those surfaces agree, that the
container ports are consistent, and that retired options have not crept back.

Run locally in the add-on container (PyYAML is installed):
    python3 scripts/verify-options.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import addon_versions

ROOT = Path(__file__).resolve().parent.parent
ADDON = ROOT / "t3_vibecoding"
CONFIG = ADDON / "config.yaml"
EN = ADDON / "translations" / "en.yaml"
FR = ADDON / "translations" / "fr.yaml"
DOCS = ADDON / "DOCS.md"
RUN = ADDON / "run.sh"
REPOSITORY = ROOT / "repository.yaml"
BUILD_WORKFLOW = ROOT / ".github" / "workflows" / "build.yml"

RETIRED_OPTIONS = {
    "t3_port",
    "t3_host",
    "t3_version",
    "code_server",
    "code_server_password",
}
RETIRED_CONFIG_KEYS = {"panel_icon", "panel_title", "ports_description"}
RETIRED_MAP_TYPES = {"config", "homeassistant_config"}


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def main() -> int:
    config = load_yaml(CONFIG)
    en_config = load_yaml(EN).get("configuration") or {}
    fr_config = load_yaml(FR).get("configuration") or {}
    en_network = load_yaml(EN).get("network") or {}
    fr_network = load_yaml(FR).get("network") or {}
    docs = DOCS.read_text(encoding="utf-8")
    runtime_files = [RUN, *sorted((ADDON / "lib").glob("*.sh"))]
    run = "\n".join(path.read_text(encoding="utf-8") for path in runtime_files)
    dockerfile = (ADDON / "Dockerfile").read_text(encoding="utf-8")

    options = config.get("options") or {}
    schema = config.get("schema") or {}
    errors: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    def option_row(name: str, text: str) -> bool:
        return re.search(rf"^\|\s*`{re.escape(name)}`\s*\|", text, re.MULTILINE) is not None

    check(
        set(options) == set(schema),
        "options and schema disagree: "
        f"only in options {sorted(set(options) - set(schema))}, "
        f"only in schema {sorted(set(schema) - set(options))}",
    )

    for name in sorted(options):
        check(name in en_config, f"option '{name}' missing from translations/en.yaml")
        check(name in fr_config, f"option '{name}' missing from translations/fr.yaml")
        check(
            re.search(rf"\b{re.escape(name)}\b", run) is not None,
            f"option '{name}' is not consumed in run.sh",
        )
        check(option_row(name, docs), f"option '{name}' has no row in DOCS.md options table")

    check(
        set(en_config) == set(fr_config),
        "translations/en.yaml and translations/fr.yaml declare different options: "
        f"only in en {sorted(set(en_config) - set(fr_config))}, "
        f"only in fr {sorted(set(fr_config) - set(en_config))}",
    )
    check(
        set(en_config) == set(options),
        "translations do not match options: "
        f"stale {sorted(set(en_config) - set(options))}, "
        f"missing {sorted(set(options) - set(en_config))}",
    )

    ports = {str(key).upper() for key in (config.get("ports") or {})}
    for lang, network in (("en", en_network), ("fr", fr_network)):
        network_ports = {str(key).upper() for key in network}
        check(
            network_ports == ports,
            f"translations/{lang}.yaml network keys do not match config.yaml ports: "
            f"stale {sorted(network_ports - ports)}, missing {sorted(ports - network_ports)}",
        )

    for field in ("webui", "watchdog"):
        value = str(config.get(field, ""))
        for port in re.findall(r"\[PORT:(\d+)\]", value):
            check(f"{port}/TCP" in ports, f"{field} references undeclared container port {port}")

    constants = dict(re.findall(r"^(T3_PORT)=(\d+)\s*$", run, re.MULTILINE))
    check(
        set(constants) == {"T3_PORT"},
        "run.sh must define the numeric T3_PORT constant",
    )
    for name, value in sorted(constants.items()):
        check(f"{value}/TCP" in ports, f"run.sh {name}={value} is not declared in config.yaml ports")
    check(
        re.search(r'^T3_HOST="0\.0\.0\.0"\s*$', run, re.MULTILINE) is not None,
        'run.sh must bind T3 to 0.0.0.0 with T3_HOST="0.0.0.0"',
    )

    check(
        re.search(r"^ARG BUILD_VERSION\s*$", dockerfile, re.MULTILINE) is not None,
        "Dockerfile must declare ARG BUILD_VERSION",
    )
    declared_args = addon_versions.read_args(dockerfile)
    for component in addon_versions.COMPONENTS:
        check(
            component.arg in declared_args,
            f"Dockerfile must declare ARG {component.arg}",
        )
    check(
        "versions.json" in dockerfile,
        "Dockerfile must write the build-time versions stamp (versions.json)",
    )
    check(
        "VERSIONS_FILE" in run,
        "runtime must read the build-time versions stamp",
    )
    check(
        "--version" not in run,
        "runtime must not probe binaries with --version; read the build stamp instead",
    )

    image = str(config.get("image") or "")
    check(image, "config.yaml must set image so the Supervisor pulls a pre-built image")
    check(
        "{" not in image,
        "config.yaml image must name the multi-arch manifest, not a {arch} variant",
    )
    check(
        ":" not in image.rsplit("/", 1)[-1],
        "config.yaml image must not carry a tag; the Supervisor uses version as the tag",
    )

    repository = str(load_yaml(REPOSITORY).get("url") or "").rstrip("/")
    owner_match = re.search(r"^https://github\.com/([^/]+)/", repository)
    check(owner_match is not None, "repository.yaml must contain a GitHub repository URL")
    check(BUILD_WORKFLOW.exists(), ".github/workflows/build.yml must exist")
    build_workflow = BUILD_WORKFLOW.read_text(encoding="utf-8") if BUILD_WORKFLOW.exists() else ""
    image_name_match = re.search(r"^\s+IMAGE_NAME:\s*(\S+)\s*$", build_workflow, re.MULTILINE)
    check(image_name_match is not None, "build workflow must define IMAGE_NAME")
    if owner_match and image_name_match:
        expected_image = f"ghcr.io/{owner_match.group(1)}/{image_name_match.group(1)}"
        check(
            image == expected_image,
            f"config.yaml image '{image}' does not match the build workflow "
            f"(expected '{expected_image}')",
        )

    for name in sorted(RETIRED_OPTIONS):
        check(name not in options, f"retired option '{name}' is back in config.yaml options")
        check(name not in schema, f"retired option '{name}' is back in config.yaml schema")
        check(name not in en_config, f"retired option '{name}' is back in translations/en.yaml")
        check(name not in fr_config, f"retired option '{name}' is back in translations/fr.yaml")
        check(
            re.search(rf"\b{re.escape(name)}\b", run) is None,
            f"retired option '{name}' is back in run.sh",
        )
        check(
            not option_row(name, docs),
            f"retired option '{name}' is back in the DOCS.md options table",
        )

    for key in sorted(RETIRED_CONFIG_KEYS):
        check(key not in config, f"retired config key '{key}' is back in config.yaml")
    map_types = {
        entry.get("type")
        for entry in (config.get("map") or [])
        if isinstance(entry, dict)
    }
    check(
        not (map_types & RETIRED_MAP_TYPES),
        f"retired map types are back in config.yaml: {sorted(map_types & RETIRED_MAP_TYPES)}",
    )

    if errors:
        print("Option truth check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"Option truth OK: {len(options)} options, {len(ports)} container ports.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
