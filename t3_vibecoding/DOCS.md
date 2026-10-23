# T3 Code + OpenCode

A **headless vibe coding** environment packaged as a local Home Assistant OS
add-on. It runs a **T3 Code** server (`t3 serve`, web mode) with **OpenCode** as
the harness, as a **non-root** user `dev` (uid/gid 1000).

## Bundled components

- `git`, `gh` (GitHub CLI)
- `node` 22 + `npm`
- `ripgrep`, `fd`, `jq`, `less`, `vim`, `nano`, `sqlite3`
- `zsh` as the default shell for `dev`, with `powerlevel10k` v1.20.0 as the
  prompt
- OpenCode TUI clipboard helpers: `xclip`, `xsel`, `wl-clipboard`, `xvfb`
  (headless Linux)
- `build-essential`, `python3` (with `pip` and PyYAML), `openssh-client`
- `@opencode/cli` 2.1.3 (OpenCode 2) and `t3` 0.1.0 (pinned stable versions,
  installed globally with npm)
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

The **container port** is fixed: `4096` for T3 Code. To change the **host**
port, use the add-on network settings in Home Assistant; `webui` and the
watchdog follow that mapping. There is no port option to fill in.

## Terminal and file editing

T3 Code already provides the shell and the file editor; the add-on ships no
separate web IDE.

- **Integrated terminal**: open it from the T3 Code toolbar or with
  `Ctrl+J` (`Cmd+J` on macOS). It is a real PTY on the add-on container, running
  as user `dev` with `HOME=/data/home` and the current project as working
  directory. The terminal is attached to a thread, so open or create a thread
  first.
- **Files panel**: browse and search the project tree, open a file from the
  panel or from a file link in the chat, and edit it in place. Saves are
  automatic. Markdown is previewed, and images, audio, video and PDF files are
  rendered in the same panel.
- **CLI editors**: `vim` and `nano` are installed for edits from the terminal.

Both surfaces are gated by the permissions of the **paired client**. The add-on
does not add a second password or port: the T3 Code session that grants the
terminal also grants file access when it is paired with the standard scopes.

### Shell and prompt

The integrated terminal runs **zsh** as user `dev`, with
[powerlevel10k](https://github.com/romkatv/powerlevel10k) v1.20.0 as its prompt.

- The first zsh session offers the powerlevel10k configuration wizard. It
  writes `~/.p10k.zsh` (`/data/home/.p10k.zsh`), which belongs to you: the
  add-on never creates or overwrites it. Re-run the wizard any time with
  `p10k configure`.
- The theme lives in `/usr/share/powerlevel10k` and is loaded from
  `/etc/zsh/zshrc`, so add-on updates replace the theme but keep your
  `~/.p10k.zsh`.
- The prompt is rendered by your browser, so the glyphs come from **your**
  machine. Install a [Nerd Font](https://www.nerdfonts.com/) locally, select it
  in the T3 Code settings (`fontFamilyTerminal`), then run `p10k configure` so
  the wizard can test it. Without a Nerd Font, accept the ASCII fallback the
  wizard offers.
- The prompt is only loaded in a real terminal. T3 also runs `zsh -ilc` without
  a TTY to read `PATH`, and the wizard must never start there.
- `bash` is still installed; `SHELL=/bin/zsh` only changes the default shell of
  the integrated terminal.

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

`env_vars` and `GH_TOKEN` are passed to **T3 Code**, which runs the terminal and
file operations as user `dev`.

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
| `/data/home` | `dev`'s `HOME`, OpenCode/gh config, secrets | yes (`/data`) |
| `/data/t3code` | `T3CODE_HOME`: userdata, caches, worktrees, logs | yes (`/data`) |
| `/share/vibecoding` | Project source code | yes (`share` folder) |

## Installation

The add-on is published as a pre-built multi-architecture image
(`ghcr.io/ericcitaire/hass-t3-vibecoding`, `amd64` and `aarch64`). Home Assistant
pulls the image tagged with the add-on version; it no longer builds the image on
the device, so installation and updates only wait for the download.

1. **Settings → Add-ons → Add-on Store → ⋮ → Repositories**, add the repository
   URL.
2. The add-on appears under the repository name.
3. **Install**, fill in the options, **Start**.
4. **Log** tab: copy the pairing token printed by `t3 serve`, then open
   `http://<box-IP>:4096/` (or the configured host port) and pair. The printed
   `Pairing URL` points at the **container IP**, which is not reachable from
   other LAN devices: keep the token and open the URL through the box IP
   instead.
5. Fine-tune in the T3 Code UI if needed (persisted in `/data`).

## Troubleshooting

- **The add-on does not start / `init: false`**: the Home Assistant base image
  ships s6-overlay v3; do not set `init: true`.
- **`gh auth login` fails**: invalid/expired token or insufficient scope
  (`repo`). Check the log.
- **JSON ignored**: an "invalid JSON" message appears in the log; fix the pasted
  content.
- **Prompt glyphs show as boxes or question marks**: the browser rendering the
  terminal has no Nerd Font. Install one on your machine, set
  `fontFamilyTerminal` in the T3 Code settings, then run `p10k configure` again
  so powerlevel10k re-tests the font.
- **Port unreachable**: check that the add-on network mapping exposes container
  port `4096`. The Supervisor watchdog tests `tcp://host:4096`.
- **Image pull fails (`manifest unknown`, `unauthorized`)**: the Supervisor pulls
  `ghcr.io/ericcitaire/hass-t3-vibecoding` with the tag matching the add-on
  `version`. Check the **Build add-on image** workflow published that version,
  and that the GHCR package is **public** (package settings → Change
  visibility): Home Assistant pulls it anonymously. Re-run the failed workflow
  after fixing it; no local rebuild is involved.
- **"Option … does not exist in the schema" warning after an update**: the old
  `t3_port`, `t3_host` and `t3_version` options were removed because they were
  not (or only partially) honoured, and `code_server` / `code_server_password`
  were removed in 0.9.0. The Supervisor ignores them; the message is harmless
  and disappears after resetting the add-on configuration.
- **Files panel says "This connection cannot read host files"**: the client is
  paired with a session that lacks the `filesystem:read` and `filesystem:write`
  scopes. Scopes are fixed when the session is created, so re-pair the client:
  revoke the old connection in T3 Code's connection settings (or use a private
  browser window), then pair again with a fresh link. The startup `Pairing URL`
  in the add-on log grants full scopes, including file access, and
  `docker exec -it -u dev -e HOME=/data/home addon_local_t3_vibecoding t3 auth pairing create --base-dir /data/t3code --base-url http://<box-IP>:4096`
  creates a fresh link with the standard scopes. Update a T3 desktop client to
  the same 0.1.x release as the server before re-pairing.
- **Old code-server data**: 0.9.0 removed code-server. Settings and extensions
  left behind are inert; reclaim the space with
  `rm -rf /data/home/.config/code-server /data/home/.local/share/code-server`.
- **Shell access when T3 is down**: install the official **Terminal & SSH**
  add-on, disable its protection mode, then run
  `docker exec -it addon_local_t3_vibecoding bash` (or find the container with
  `docker ps --filter name=t3_vibecoding`). This is a break-glass path, not a
  second web terminal.
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

`@opencode/cli` and `t3` versions are pinned in the `Dockerfile` through the
`OPENCODE_VERSION` and `T3_VERSION` build args (currently `2.1.3` and `0.1.0`).
To refresh the applications:

1. look up the latest stable version on npm (`npm view @opencode/cli version`,
   `npm view t3 version`);
2. update the `ARG` defaults in the `Dockerfile`;
3. bump `version` in `config.yaml` and add a `CHANGELOG.md` entry;
4. merge to `main`.

The **Build add-on image** workflow then extracts `version` from `config.yaml`,
builds `amd64` and `aarch64` on native runners, and publishes the version and
`latest` tags to GHCR as one multi-arch manifest. The Supervisor pulls
`ghcr.io/ericcitaire/hass-t3-vibecoding:<version>`. A version that was already
published is rebuilt but not overwritten, so every release needs a version bump.

The versions actually bundled are written at build time into
`/etc/t3-vibecoding/versions.json` and logged at startup. No binary is probed at
runtime.

Changing an `ARG` value invalidates the Docker cache of the affected layers, so
the new version is really installed (unlike a rebuild with an unchanged
`Dockerfile`). Avoid `t3 update` inside the container: the update would be lost
on the next image build and is less reproducible.

When bumping `T3_VERSION`, the browser package list (`browser-packages.txt`) is
checked against T3's own `DEBIAN_PACKAGES` by CI. Update it if that check fails.
