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
- PDF tooling: `poppler-utils` (`pdftotext`, `pdfinfo`, `pdftoppm`,
  `pdfimages`), `python3-pil` (Pillow) and `python3-pymupdf` (PyMuPDF). They
  are Debian packages because the image's Python is externally managed:
  `pip install` fails without `--break-system-packages`. PyMuPDF extracts text
  and renders pages, including large scanned documents; Pillow saves the
  rendered images. `qpdf`, Ghostscript and ImageMagick are intentionally not
  installed.
- `@opencode/cli` 2.2.6 (OpenCode 2) and `t3` 0.1.7 (pinned stable versions,
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
- The theme lives in `/usr/share/powerlevel10k`. It is loaded by a short block
  the add-on keeps at the end of `~/.zshrc`, so add-on updates replace the
  theme but keep your `~/.p10k.zsh`. The block is re-added on start if you
  remove it; when `~/.zshrc` does not exist, it is created with only that
  block.
- The block must stay at the end of the file: powerlevel10k has to be sourced
  after your completion setup (`compinit`), otherwise the *first* prompt is
  drawn by the previous shell prompt and the theme only appears from the
  second one.
- Instant prompt is enabled when the cache written by the wizard is present. If
  it is not, the add-on's block falls back to the synchronous path so the first
  prompt is still drawn instead of being swallowed.
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

Example: enable the OpenCode driver and start new threads on a free model.

```json
{
  "providers": {
    "opencode": { "enabled": true }
  },
  "textGenerationModelSelection": {
    "instanceId": "opencode",
    "model": "opencode/deepseek-v4.1-flash-free"
  }
}
```

Drivers available under `providers`: `opencode`, `codex`, `claudeAgent`,
`cursor`, `grok`, `antigravity` — each with an `enabled` field (default
`false`).

The add-on does not route between models: there is no gateway in the image and
no automatic failover. When a free model is rate-limited, the turn fails and you
pick another model from the T3 Code selector, for example a paid one from your
own provider. Free models are free for a limited time and rotate; prefer the
zero-retention ones (`deepseek-v4.1-flash-free`, `glm-5.3-flash-free`) over
those that may use prompts for training.

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
| `/tmp/opencode` | Scratch directory T3 Code points agents at, owned by `dev` | no (container) |

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
- **The Release workflow fails with `Resource not accessible by integration`**:
  the repository does not let workflows create pull requests. Enable **Settings
  → Actions → General → Workflow permissions → Allow GitHub Actions to create
  and approve pull requests**, then re-run the workflow. The release branch is
  pushed before that step, so a re-run reuses it.
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
- **PDF tools missing** (`pdftotext: command not found`,
  `ModuleNotFoundError: No module named 'pymupdf'`): the running image predates
  the bundled PDF stack. Pull or rebuild the add-on instead of running
  `pip install`: the image's Python is externally managed and pip refuses
  without `--break-system-packages`.
- **Headless keyring**: `@napi-rs/keyring` may not find a Secret Service; check
  the file fallback in the logs.
- **Network security**: port `4096` (bound to `0.0.0.0` in the container) is
  exposed to the LAN; rely on T3 auth and avoid direct Internet exposure
  (prefer Tailscale).

## Updates

The add-on pins three components in the `Dockerfile`, as build args:
`@opencode/cli` (`OPENCODE_VERSION`), `t3` (`T3_VERSION`) and `powerlevel10k`
(`POWERLEVEL10K_VERSION`). The versions bundled in a given image are listed
under **Bundled components** above and stamped at build time into
`/etc/t3-vibecoding/versions.json`.

A **release workflow** keeps them current; you do not bump versions by hand:

- **Weekly** (Monday, 06:00 UTC) it compares the pinned versions with the
  versions published upstream: the npm `latest` dist-tag for `@opencode/cli` and
  `t3`, and the newest semantic-version tag for `powerlevel10k`. The
  `preview` and `nightly` channels are ignored. It also reads the
  `## Unreleased` section of `CHANGELOG.md`.
- When a version moved or `Unreleased` has content, it opens — or refreshes in
  place on the existing `chore/dependency-sweep` branch — one **release PR**
  carrying everything in a single commit: the build args, `version` in
  `config.yaml`, the new `CHANGELOG.md` entry and the versions quoted in this
  file. The staged `Unreleased` bullets are folded into the new entry, followed
  by the component bullets under `### Bundled components`.
- **Monthly** (1st, 06:00 UTC) it also publishes a patch release that changes no
  component, so Debian and `apt` security fixes reach the image. It stands down
  when a release was published in the previous seven days.

Every user-visible change adds a bullet under `## Unreleased` in `CHANGELOG.md`,
grouped under `### Added`, `### Changed` or `### Fixed`. The bump follows those
sections: anything under `Added` or `Changed` opens a **minor** release, a
`Fixed`-only release is a **patch**, and a dependency-only release follows the
upstream bump as before. The `changelog` CI job fails a pull request that
touches a user-visible file without a new bullet; add the `skip-changelog`
label when the change is internal. Documentation-, CI- and test-only pull
requests are exempt, and so is the release PR, which drains `## Unreleased`.

Reviewing the release PR is the only manual step: merging it is the release.
Before that, the workflow runs the whole `Verify add-on` suite on its branch,
including `scripts/verify-versions.py`, which fails when `config.yaml`, the top
`CHANGELOG.md` entry, the `DOCS.md` quotes and the `Dockerfile` build args
disagree, when the CHANGELOG stops decreasing, when `Unreleased` contains an
unknown section or a placeholder, or when a `TODO` survives into a releasable
entry.

Run it by hand from **Actions → Release → Run workflow**: `release_now` cuts a
release even when nothing moved and `Unreleased` is empty (a package refresh),
and `kind` forces `patch` or `minor` instead of deriving it from the staged
sections. Merging to `main` is not how a version is released: `version` is
bumped only inside a release PR.

> **One-time repository setting**: the release workflow opens its PR with the
> `GITHUB_TOKEN`, so **Settings → Actions → General → Workflow permissions** must
> allow **Allow GitHub Actions to create and approve pull requests**. Without it
> the run fails at the last step; the branch is already pushed and will be
> reused on the next run.

The **Build add-on image** workflow then extracts `version` from `config.yaml`,
builds `amd64` and `aarch64` on native runners, and publishes the version and
`latest` tags to GHCR as one multi-arch manifest. The Supervisor pulls
`ghcr.io/ericcitaire/hass-t3-vibecoding:<version>`. Once the manifest is
published and the push bumped `version`, the workflow creates the annotated tag
`v<version>` on the release commit and a GitHub Release whose body is the
`CHANGELOG.md` entry for that version. A version that was already published is
rebuilt but not overwritten, so every release needs a version bump; an existing
tag or Release is left alone.

The versions actually bundled are written at build time into
`/etc/t3-vibecoding/versions.json` and logged at startup. No binary is probed at
runtime.

Changing an `ARG` value invalidates the Docker cache of the affected layers, so
the new version is really installed (unlike a rebuild with an unchanged
`Dockerfile`). Avoid `t3 update` inside the container: the update would be lost
on the next image build and is less reproducible.

When bumping `T3_VERSION`, the browser package list (`browser-packages.txt`) is
checked against T3's own `DEBIAN_PACKAGES` by CI. Update it if that check fails.
