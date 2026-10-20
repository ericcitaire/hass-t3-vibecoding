# T3 Code + OpenCode

A **headless vibe coding** environment packaged as a local Home Assistant OS
add-on. It runs a **T3 Code** server (`t3 serve`, web mode) with **OpenCode** as
the harness, as a **non-root** user `dev` (uid/gid 1000).

## Bundled components

- `git`, `gh` (GitHub CLI)
- `node` 22 + `npm`
- `ripgrep`, `fd`, `jq`, `less`, `vim`, `nano`
- `build-essential`, `python3` (with `pip` and PyYAML), `openssh-client`
- `opencode-ai` 1.19.3 and `t3` 0.1.0 (pinned stable versions, installed
  globally with npm)
- `code-server` 4.141.0 (VS Code in the browser, optional)
- System libraries and fonts for T3's headless preview browser
  (Chromium/Playwright)

## Options

| Option | Default | Description |
|---|---|---|
| `workspace` | `/share/vibecoding` | Default working/project directory. |
| `git_name` | *(empty)* | Global git `user.name` for `dev`. |
| `git_email` | *(empty)* | Global git `user.email` for `dev`. |
| `github_token` | *(empty)* | GitHub token for `gh auth login` (+ exports `GH_TOKEN`). |
| `env_vars` | `[]` | Environment variables passed to T3 Code. |
| `opencode_config_json` | *(empty)* | JSON → `~/.config/opencode/opencode.json`. |
| `opencode_auth_json` | *(empty)* | JSON → `~/.local/share/opencode/auth.json`. |
| `t3_settings_json` | *(empty)* | JSON merged into `<T3CODE_HOME>/userdata/settings.json`. |
| `code_server` | `false` | Enables the **code-server** web editor (VS Code) on port `8081`. |
| `code_server_password` | *(empty)* | code-server password. **Required** when `code_server` is enabled. |

The **container ports** are fixed: `4096` for T3 Code and `8081` for
code-server. To change the **host** port, use the add-on network settings in
Home Assistant; `webui` and the watchdog follow that mapping. There is no port
option to fill in.

## Optional code-server web editor

In addition to T3 Code, the add-on can run **code-server**, a full VS Code
instance in the browser (editor, terminal, LSP, Open VSX extensions).

1. Set `code_server_password` (masked option).
2. Check `code_server`.
3. Start / restart the add-on.
4. Open `http://<box-IP>:8081/` and sign in with that password.

Important points:

- The port is **fixed** (`8081`) and separate from T3 Code (`4096`).
  code-server is not exposed through Home Assistant ingress (sub-paths are not
  supported): open it in a separate tab.
- If `code_server` is enabled without a password, code-server is **not**
  started and a warning appears in the log.
- The password is rewritten into `~/.config/code-server/config.yaml` at every
  start: changing it from the code-server UI is not persistent, use the add-on
  option.
- code-server runs as user `dev`, with the same `HOME` and workspace as T3 Code
  (`/share/vibecoding` by default).
- code-server runs as a supervised **s6 service**: it restarts automatically if
  it stops, and stops cleanly with the add-on.
- The password and port grant **full shell access**: do not expose `8081` to the
  Internet. Stay on the LAN or use a VPN (Tailscale, etc.).
- Settings and extensions persist in `/data/home/.local/share/code-server`;
  configuration lives in `/data/home/.config/code-server`.
- Extensions come from **Open VSX** (the Microsoft marketplace is not reachable
  from code-server).

## Provider / API key configuration

T3 Code delegates authentication to its *drivers* (OpenCode, Codex, Claude,
Cursor, Grok). Credentials are therefore configured **upstream**, from the
add-on.

### 1. Environment variables (simplest)

`env_vars` field: a list of `name` / `value` pairs. Examples of keys recognised
by OpenCode:

```yaml
env_vars:
  - name: ANTHROPIC_API_KEY
    value: "sk-ant-..."
  - name: OPENAI_API_KEY
    value: "sk-..."
  - name: OPENROUTER_API_KEY
    value: "sk-or-..."
```

Values use the `password` type (masked in the UI).

`env_vars` and `GH_TOKEN` are passed to **both T3 Code and code-server**, which
share the same runtime environment.

### 2. OpenCode config (JSON)

Paste the contents of `~/.config/opencode/opencode.json` (providers, models,
options) into `opencode_config_json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "anthropic/claude-sonnet-4-5",
  "provider": {
    "anthropic": { "options": { "apiKey": "sk-ant-..." } }
  }
}
```

### 3. OpenCode auth (JSON)

For credentials in the `opencode auth` format (api/oauth), paste the contents of
`~/.local/share/opencode/auth.json` into `opencode_auth_json`.

> JSON is validated with `jq` at startup, then written before T3 Code starts.
> Invalid JSON is ignored with a warning in the log.

### 4. T3 Code settings (`settings.json`)

By default **no driver is enabled** in T3 Code, and the default generation model
points at `codex` (unavailable here). To make the add-on usable out of the box,
set `t3_settings_json`. This JSON is **recursively merged** into
`<T3CODE_HOME>/userdata/settings.json`: your keys win, and the others (settings
made in the UI) are preserved.

Example: enable the OpenCode driver and use DeepSeek by default.

```json
{
  "providers": {
    "opencode": { "enabled": true }
  },
  "textGenerationModelSelection": {
    "instanceId": "opencode",
    "model": "deepseek/deepseek-chat"
  }
}
```

Drivers available under `providers`: `opencode`, `codex`, `claudeAgent`,
`cursor`, `grok`, `antigravity` — each with an `enabled` field (default
`false`).

> The file lives in `/data/t3code/userdata/settings.json` and survives add-on
> updates.

### 5. GitHub CLI (`gh`)

Set `github_token` (classic PAT, `repo` scope): the add-on runs
`gh auth login --with-token` + `gh auth setup-git`, and exports `GH_TOKEN`. The
configuration persists in `/data/home/.config/gh`.

## Persistence

| Container path | Content | Persistent |
|---|---|---|
| `/data/home` | `dev`'s `HOME`, OpenCode/gh/code-server config, secrets | yes (`/data`) |
| `/data/home/.local/share/code-server` | code-server settings and extensions | yes (`/data`) |
| `/data/t3code` | `T3CODE_HOME`: userdata, caches, worktrees, logs | yes (`/data`) |
| `/share/vibecoding` | Project source code | yes (`share` folder) |

## Installation

1. **Settings → Add-ons → Add-on Store → ⋮ → Repositories**, add the repository
   URL.
2. The add-on appears under the repository name.
3. **Install**, fill in the options, **Start**.
4. **Log** tab: copy the pairing information printed by `t3 serve`, then open
   `http://<box-IP>:4096/` (or the configured host port) and pair.
5. *(Optional)* Enable `code_server`, set `code_server_password`, then open
   `http://<box-IP>:8081/`.
6. Fine-tune in the T3 Code UI if needed (persisted in `/data`).

## Troubleshooting

- **The add-on does not start / `init: false`**: the Home Assistant base image
  ships s6-overlay v3; do not set `init: true`.
- **`gh auth login` fails**: invalid/expired token or insufficient scope
  (`repo`). Check the log.
- **JSON ignored**: an "invalid JSON" message appears in the log; fix the pasted
  content.
- **Port unreachable**: check that the add-on network mapping exposes container
  port `4096` (or `8081` for code-server). The Supervisor watchdog tests
  `tcp://host:4096`.
- **"Option … does not exist in the schema" warning after an update**: the old
  `t3_port`, `t3_host` and `t3_version` options were removed because they were
  not (or only partially) honoured. The Supervisor ignores them; the message is
  harmless and disappears after resetting the add-on configuration.
- **code-server does not start**: check that `code_server_password` is set and
  that port `8081` is free on the host. Errors and restarts appear in the
  add-on log.
- **code-server password rejected**: the password is rewritten from the
  `code_server_password` option at every start; changing it in the editor is not
  enough.
- **`OpenCode CLI version probe timed out after 4 seconds`**: the OpenCode
  binary can take more than 4 seconds to start on some machines, while T3 Code
  enforces that timeout on `opencode --version`. The add-on installs a wrapper
  that answers `--version` immediately; other commands are forwarded to the real
  binary. If the message persists, check that no custom `binaryPath` points
  directly at `opencode.real`.
- **Preview unavailable**: if T3 reports "This host is missing libraries T3's
  browser needs (…)" or "inline preview unavailable on this host", the headless
  browser libraries are missing from the image. They are normally installed by
  the `Dockerfile`: check that the add-on was **rebuilt** (not just restarted).
  The browser itself (`chrome-headless-shell`, ~115 MiB) is downloaded by T3 on
  first use into `/data/t3code/tools`: that first run needs network access to
  `storage.googleapis.com`, then the binary persists in `/data`.
- **Headless keyring**: `@napi-rs/keyring` may not find a Secret Service; check
  the file fallback in the logs.
- **Network security**: port `4096` (bound to `0.0.0.0` in the container) is
  exposed to the LAN; rely on T3 auth and avoid direct Internet exposure
  (prefer Tailscale).

## Updates

`opencode-ai`, `t3` and `code-server` versions are pinned in the `Dockerfile`
through the `OPENCODE_VERSION`, `T3_VERSION` and `CODE_SERVER_VERSION` build
args (currently `1.19.3`, `0.1.0` and `4.141.0`). To refresh the applications:

1. look up the latest stable version on npm (`npm view opencode-ai version`,
   `npm view t3 version`) and in the code-server GitHub releases;
2. update the `ARG` defaults in the `Dockerfile`;
3. bump `version` in `config.yaml` and add a `CHANGELOG.md` entry;
4. rebuild the add-on.

The versions actually bundled are written at build time into
`/etc/t3-vibecoding/versions.json` and logged at startup. No binary is probed at
runtime.

Changing an `ARG` value invalidates the Docker cache of the affected layers, so
the new version is really installed (unlike a rebuild with an unchanged
`Dockerfile`). Avoid `t3 update` inside the container: the update would be lost
on rebuild and is less reproducible.

When bumping `T3_VERSION`, the browser package list (`browser-packages.txt`) is
checked against T3's own `DEBIAN_PACKAGES` by CI. Update it if that check fails.
