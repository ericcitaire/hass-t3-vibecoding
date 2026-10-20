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

## Checks

CI verifies that options stay consistent across `config.yaml`, translations,
`DOCS.md` and `run.sh`, that container ports agree, and that the browser package
list matches the one embedded in T3 Code:

```bash
python3 scripts/verify-options.py
bash tests/test-startup.sh
bash tests/test-code-server.sh
bash tests/test-credentials.sh
# With a t3 binary from the installed npm package:
python3 scripts/verify-browser-packages.py --binary /path/to/t3
```

The add-on image ships Python and PyYAML, so `verify-options.py` runs without
installing anything.
