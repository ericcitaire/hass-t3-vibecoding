# Changelog

## Unreleased

## 0.19.1

### Fixed

- Start T3 Code through the default `t3` command instead of `t3 serve`: since
  t3 0.1.11 `serve` no longer accepts `--auto-bootstrap-project-from-cwd`, so
  the add-on exited at startup with `Unrecognized flag` and the workspace
  project was never created. The workspace is bootstrapped again on first
  launch.

## 0.19.0

### Changed

- Make `bash` the default shell of the integrated terminal again and drop
  `zsh` and `powerlevel10k`. The prompt is now a short block appended to
  `/etc/bash.bashrc` (colour, current git branch, 5000-entry history in
  `/data/home`, `bash-completion`); no file is written to the persistent home,
  and powerlevel10k is no longer a tracked component.

### Added

- Bundle the Claude Code CLI (`@anthropic-ai/claude-code` 2.1.331) so T3's
  `claudeAgent` driver runs out of the box, and track it in the dependency
  sweep through the `CLAUDE_CODE_VERSION` build arg.
- Bundle the OpenAI Codex CLI (`@openai/codex` 0.172.0) for T3's `codex` driver
  and the GitHub Copilot CLI (`@github/copilot` 1.0.115) for the integrated
  terminal, tracked through the `CODEX_VERSION` and `COPILOT_VERSION` build
  args.

### Bundled components

- Update `@opencode/cli` from 2.3.0 to **2.4.1** (the `OPENCODE_VERSION` build
  arg default). Release notes:
  https://www.npmjs.com/package/@opencode/cli/v/2.4.1
- Update `t3` from 0.1.9 to **0.1.11** (the `T3_VERSION` build arg default).
  Release notes: https://www.npmjs.com/package/t3/v/0.1.11

## 0.18.0

### Bundled components

- Update `@opencode/cli` from 2.2.6 to **2.3.0** (the `OPENCODE_VERSION` build
  arg default). Release notes:
  https://www.npmjs.com/package/@opencode/cli/v/2.3.0
- Update `t3` from 0.1.8 to **0.1.9** (the `T3_VERSION` build arg default).
  Release notes: https://www.npmjs.com/package/t3/v/0.1.9

## 0.17.0

### Added

- Ship `python3-reportlab` (ReportLab) so agents can generate new PDFs, not
  just read them.

### Bundled components

- Update `t3` from 0.1.7 to **0.1.8** (the `T3_VERSION` build arg default).
  Release notes: https://www.npmjs.com/package/t3/v/0.1.8

## 0.16.0

### Added

- Ship PDF tooling for real documents: `poppler-utils` (`pdftotext`, `pdfinfo`,
  `pdftoppm`, `pdfimages`), `python3-pymupdf` for fast text extraction and page
  rendering, and `python3-pil` to save rendered pages.
  [#13](https://github.com/ericcitaire/hass-t3-vibecoding/pull/13)

### Bundled components

- Update `@opencode/cli` from 2.2.5 to **2.2.6** (the `OPENCODE_VERSION` build
  arg default). Release notes:
  https://www.npmjs.com/package/@opencode/cli/v/2.2.6
- Update `t3` from 0.1.6 to **0.1.7** (the `T3_VERSION` build arg default).
  Release notes: https://www.npmjs.com/package/t3/v/0.1.7

## 0.15.1

- Update `@opencode/cli` from 2.2.0 to **2.2.5** (the `OPENCODE_VERSION` build
  arg default). Release notes:
  https://www.npmjs.com/package/@opencode/cli/v/2.2.5
- Update `t3` from 0.1.3 to **0.1.6** (the `T3_VERSION` build arg default).
  Release notes: https://www.npmjs.com/package/t3/v/0.1.6

## 0.15.0

- Update `@opencode/cli` from 2.1.3 to **2.2.0** (the `OPENCODE_VERSION` build
  arg default). Release notes:
  https://www.npmjs.com/package/@opencode/cli/v/2.2.0
- Update `t3` from 0.1.0 to **0.1.3** (the `T3_VERSION` build arg default).
  Release notes: https://www.npmjs.com/package/t3/v/0.1.3

## 0.14.1

- Fix the prompt of the integrated terminal: the **first** prompt was drawn by
  the shell's previous prompt and powerlevel10k only appeared from the second
  one. The theme was sourced from `/etc/zsh/zshrc`, which zsh reads before
  `~/.zshrc`, so it ran before the user's `compinit`; powerlevel10k skips its
  first paint in that case, and paints nothing at all when the instant-prompt
  cache does not exist yet. The theme is now sourced by a short managed block
  kept at the end of `~/.zshrc` (created with only that block when the file is
  missing, re-added on start if removed), and the block falls back to the
  synchronous path when the wizard's instant-prompt cache is absent. The
  system file keeps `compinit` and the history settings. `~/.p10k.zsh` is still
  never created or overwritten by the add-on. A CI test now drives a real PTY
  and asserts that the first prompt is powerlevel10k's.

## 0.14.0

- Install `powerlevel10k` v1.20.0 (the `POWERLEVEL10K_VERSION` build arg
  default) and make `zsh` the default shell of the integrated terminal, so the
  prompt is styled without users installing anything. The theme is unpacked
  from the pinned upstream tarball into `/usr/share/powerlevel10k` and loaded
  from `/etc/zsh/zshrc`; loading is skipped when the shell has no TTY, because
  T3 reads `PATH` through `zsh -ilc` at startup and the configuration wizard
  must not run there. The wizard writes `~/.p10k.zsh` on first use: that file
  stays a user file and is never seeded by the add-on. `SHELL=/bin/zsh` is
  exported to `dev` (that is how T3 chooses the terminal shell), and `bash`
  remains installed for users who prefer it.

## 0.13.1

- Update `@opencode/cli` from 2.1.2 to **2.1.3** (the
  `OPENCODE_VERSION` build arg default). No configuration or compatibility
  change expected; T3 Code keeps probing the CLI through the same `--version`
  wrapper. The version is bumped separately from 0.13.0 because that image tag
  was already published: the build workflow skips tags that exist, so the
  rebuilt image was never pushed.

## 0.13.0

- Add `zsh` to the image alongside `bash`, `vim` and `nano`, so users can
  switch their interactive shell without installing anything.

## 0.12.0

- Shrink the pre-built image. The npm install, the OpenCode `--version`
  wrapper and the cleanup now run in a single layer, dropping the npm cache
  (`/root/.npm`), the unused OpenCode baseline platform package
  (`@opencode/cli-linux-*-baseline`, never selected by the postinstall) and the
  duplicate left by the wrapper's `mv`. The wrapper still answers
  `opencode --version` from `package.json` and forwards every other argument to
  `opencode.real`.

## 0.11.0

- Update OpenCode from `opencode-ai` 1.19.3 to **OpenCode 2** (`@opencode/cli`
  2.1.2). T3 Code 0.1.0 reports limited compatibility with OpenCode 1.x and
  needs `>=2.0.18`; OpenCode 2 is published under the new `@opencode/cli`
  package, so the image install and the version-probe wrapper path change with
  it. Config and auth still live in `~/.config/opencode` and
  `~/.local/share/opencode`.
- Keep the `--version` wrapper (answers instantly from `package.json`, forwards
  everything else to the real binary) because T3 probes the CLI with a 4 second
  timeout.

## 0.10.0

- Publish the add-on as a **pre-built multi-architecture image**
  (`ghcr.io/ericcitaire/hass-t3-vibecoding`, `amd64` and `aarch64`) and point
  `config.yaml` at it. Installation and updates now download the image tagged
  with the add-on version instead of building it on the Home Assistant device,
  which removes the long install time.
- Add `.github/workflows/build.yml`: builds both architectures on native GitHub
  runners, publishes the version and `latest` tags to GHCR, creates the
  multi-arch manifest and signs it with Cosign.
- `scripts/verify-options.py` now checks that `config.yaml` names the
  multi-arch image, without a tag or `{arch}` placeholder, and that the name
  matches the build workflow.
- Document the release flow, GHCR package visibility and image-pull
  troubleshooting.

## 0.9.0

- **Breaking**: remove the bundled **code-server** web IDE. T3 Code 0.1.0
  already provides an integrated terminal and an editable Files panel, so the
  second port, password, s6 service and VS Code image were unused weight.
- Drop the `code_server` and `code_server_password` options and the `8081`
  container port. Existing values are ignored by the Supervisor and can be
  reset; remove `/data/home/.config/code-server` and
  `/data/home/.local/share/code-server` to reclaim disk space.
- Remove the code-server download from the image, the `CODE_SERVER_VERSION`
  build arg, its `versions.json` entry, the s6 service, `lib/code-server.sh`,
  tests and CI steps.
- Document the integrated terminal, the Files panel and how to re-pair a client
  that reports "This connection cannot read host files". File and terminal
  access are scoped at pairing time; sessions persist across add-on updates.
- Add tools OpenCode uses or documents that the image was missing: `sqlite3`
  for the `opencode db` shell, and `xclip`, `xsel`, `wl-clipboard` and `xvfb`
  for TUI copy/paste, including headless Linux.

## 0.8.2

- Install the system libraries and fonts required by T3 Code's headless preview
  browser (`chrome-headless-shell`) in the image. Fixes "This host is missing
  libraries T3's browser needs" / "inline preview unavailable on this host".
- The browser itself is still downloaded by T3 on first use into
  `/data/t3code/tools`, so it persists and adds no image cost.
- Move the browser package list to `browser-packages.txt`; a CI job compares it
  with the `DEBIAN_PACKAGES` list embedded in T3 Code.
- Ship `python3-pip` and `python3-yaml` so `scripts/verify-options.py` runs in
  the add-on container without bootstrapping pip.
- Add ShellCheck and Hadolint CI jobs.
- All Markdown documentation is now in English; shell log messages and the
  add-on description follow the same rule.

## 0.8.1

- Bundled versions (`opencode`, `t3`, `code-server`, add-on version) are written
  at build time into `/etc/t3-vibecoding/versions.json`.
- Startup reads that file instead of probing three binaries (`--version`), which
  removes three subprocesses and code-server's temporary XDG tree.
- The CI checker ensures the stamp exists and that no runtime `--version` probe
  creeps back in.

## 0.8.0

- Credential and configuration intake is centralised in `lib/credentials.sh`:
  JSON validation, atomic writes, permissions, `gh auth`, T3 settings merge, and
  environment construction.
- T3 Code and code-server now receive exactly the same environment (`GH_TOKEN`,
  `env_vars`).
- A `gh auth setup-git` failure is logged instead of being silent.
- Log a summary of the applied credentials/configuration, without any secret
  values.
- Add `tests/test-credentials.sh` and factor the tests into `tests/helpers.sh`.

## 0.7.0

- **code-server** becomes a supervised **s6** service
  (`services/code-server/run`) instead of a `while true` loop in `run.sh`. s6
  handles startup, restart and clean shutdown alongside T3 Code.
- code-server preparation (password, `config.yaml`, permissions) lives in
  `lib/code-server.sh` and is no longer run by the entry script.
- code-server now receives the same environment as T3 Code (`GH_TOKEN`,
  `env_vars`).
- Add `tests/test-code-server.sh`, run by CI.

## 0.6.1

- Extract a startup module (`lib/startup.sh`): option loading, `HOME`
  preparation, atomic JSON writes, `dev` environment construction, and T3 Code
  launch. `run.sh` is now limited to orchestration.
- Add `tests/test-startup.sh` (4 tests without a container), run by CI.

## 0.6.0

- Remove misleading options: `t3_port`, `t3_host` and `t3_version` were not (or
  only partially) honoured. The T3 Code container port is fixed at `4096`,
  listening on `0.0.0.0`, and only the **host** port is configured in the
  add-on network settings.
- Remove dead surfaces: the `config` mount (deprecated and unused),
  `panel_icon`/`panel_title` (no ingress) and `ports_description` (duplicate of
  the translations).
- Add `scripts/verify-options.py` and a GitHub Action that check option / schema
  / translation / `DOCS.md` / port / `run.sh` consistency.
- Delete `PLAN.md`, an obsolete and contradictory implementation plan.

## 0.5.1

- Fix the T3 Code OpenCode health check: `opencode --version` could exceed the
  4-second timeout (`OpenCode CLI version probe timed out after 4 seconds`)
  because of the compiled binary's startup time.
- A lightweight wrapper answers `opencode --version` immediately; all other
  commands are forwarded to the real `opencode.real` binary.

## 0.5.0

- Add **code-server 4.141.0** (VS Code in the browser), installed from the
  official GitHub release and pinned through `CODE_SERVER_VERSION`.
- New `code_server` (disabled by default) and `code_server_password` options to
  enable and protect the web editor from the Home Assistant configuration UI.
- Dedicated port `8081` (T3 Code stays on `4096`); code-server runs as user
  `dev`, alongside `t3 serve`, and restarts automatically if it stops.
- code-server configuration and extensions persist in `/data/home`.
- `en`/`fr` translations and documentation updated.

## 0.4.0

- Update bundled applications: **OpenCode 1.19.3** and **T3 Code 0.1.0** (latest
  stable versions published on npm).
- Versions are pinned through the `OPENCODE_VERSION` and `T3_VERSION` build
  args: the Docker cache for the npm layer is invalidated when a version
  changes, ensuring the rebuilt image really contains the new version.
- Log the `opencode` and `t3` versions at add-on startup.

## 0.3.0

- `t3_settings_json` option: JSON recursively merged into
  `<T3CODE_HOME>/userdata/settings.json` to enable drivers and define default
  behaviour (generation model). Makes it possible to enable the OpenCode harness
  without going through the UI.
- JSON validation with `jq`; merge without overwriting settings made in the UI.
- Translate the new option (`en`/`fr`).

## 0.2.0

- `github_token` option: `gh auth login --with-token` + `gh auth setup-git`, and
  export `GH_TOKEN`.
- `env_vars` option (name/value list): environment variables passed to T3 Code
  (provider API keys).
- `opencode_config_json` option: writes `~/.config/opencode/opencode.json`.
- `opencode_auth_json` option: writes `~/.local/share/opencode/auth.json`.
- JSON validation with `jq` (invalid JSON ignored with a warning).
- New translations for the added options.

## 0.1.0

- Initialise the local "T3 Code + OpenCode" add-on.
- Debian (glibc) image with developer tooling: git, gh, node 22, npm, ripgrep,
  fd, jq, build-essential, python3, openssh-client.
- Global installation of `opencode-ai` and `t3`.
- Non-root `dev` user (uid/gid 1000).
- `run.sh`: prepare persistent directories, configure git, then `exec t3 serve`
  (web mode) as `dev`.
- Persistence in `/data/home` and `/data/t3code`, workspace on
  `/share/vibecoding`.
- `en`/`fr` translations.
