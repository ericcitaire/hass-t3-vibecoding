# Home Assistant add-ons by Eric

Local add-on repository for Home Assistant OS.

## Adding this repository to Home Assistant

1. **Settings → Add-ons → Add-on Store**.
2. **⋮ → Repositories**.
3. Paste the repository URL:
   - Public repository: `https://github.com/ericcitaire/hass-t3-vibecoding`
   - Private repository: `https://<TOKEN>@github.com/ericcitaire/hass-t3-vibecoding`
     (GitHub *personal access token* with the `repo` scope).
4. **Add**, then reload the page. The add-ons appear under the repository name.

## Add-ons

| Add-on | Description |
|---|---|
| [T3 Code + OpenCode](t3_vibecoding) | Headless vibe coding: T3 Code server + OpenCode, developer tooling, non-root user. |

## Pre-built images

The add-on image is built and published to GitHub Container Registry by
[`.github/workflows/build.yml`](.github/workflows/build.yml) on every push to
`main` that touches `t3_vibecoding/`, and by manual dispatch. The add-on
`config.yaml` points at the multi-arch manifest
`ghcr.io/ericcitaire/hass-t3-vibecoding`; the Supervisor pulls the tag matching
the add-on `version` instead of building on the device.

- `amd64` and `aarch64` are built on native GitHub runners and combined into
  one multi-arch manifest.
- Images are tagged with the add-on version and `latest`, and signed with
  Cosign.
- Publish a release by bumping `version` in `t3_vibecoding/config.yaml` and
  merging to `main`. An already published version is rebuilt but not
  overwritten.
- The GHCR package must be **public** so Home Assistant can pull it anonymously
  (package settings → Change visibility). The first publish may create it
  private.

## Checks

CI verifies that options stay consistent across `config.yaml`, translations,
`DOCS.md` and `run.sh`, that container ports agree, that the configured image
matches the build workflow, and that the browser package list matches the one
embedded in T3 Code:

```bash
python3 scripts/verify-options.py
bash tests/test-startup.sh
bash tests/test-credentials.sh
# With a t3 binary from the installed npm package:
python3 scripts/verify-browser-packages.py --binary /path/to/t3
```

The add-on image ships Python and PyYAML, so `verify-options.py` runs without
installing anything.
