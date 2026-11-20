# T3 Code add-on

Home Assistant add-on that runs a headless T3 Code server with OpenCode.

## Language

**Inline preview**:
HTML rendered directly inside the conversation for the reader.
_Avoid_: Preview, browser preview

**Server browser**:
Browser run by the T3 server for live preview tabs and page inspection.
_Avoid_: Browser, Chrome, Playwright

**Agent browser access**:
T3 setting that lets an agent session use the server browser's tools.
_Avoid_: Browser mode, preview access

**Integrated terminal**:
Terminal opened from the T3 Code UI and attached to a thread, running in the
add-on container as `dev`.
_Avoid_: Web terminal, shell add-on

**Files panel**:
T3 Code surface for browsing the project and editing workspace files in place.
_Avoid_: File explorer, web editor

**Web IDE**:
Full browser-based IDE served by the add-on itself, as code-server was; the
add-on does not provide one.
_Avoid_: Files panel, editor

**Model gateway**:
Service between the agent and the model providers that chooses which upstream
serves a request; the add-on does not provide one.
_Avoid_: Router, model router, proxy, CLIProxyAPI

**Pairing**:
One-time exchange that links a client to the T3 Code server.
_Avoid_: Login, sign-in

**Pre-built image**:
Multi-architecture add-on image published to GHCR by CI and pulled by the
Supervisor, instead of being built on the device.
_Avoid_: Docker image, container

**Scope**:
Permission granted to a paired client for the lifetime of its session.
_Avoid_: Role, permission level

**Add-on version**:
The version of the packaged add-on, which is also the tag of its published
image.
_Avoid_: Image tag, build number

**Release surface**:
One of the four files that must agree for a release: the Dockerfile build args,
`version` in `config.yaml`, the top `CHANGELOG.md` entry, and the component
versions quoted in `DOCS.md`.
_Avoid_: Release file, metadata file

**Release workflow**:
Scheduled workflow that compares the component versions pinned in the image
with the versions published upstream, folds the CHANGELOG's `## Unreleased`
section into a version entry, and opens the release PR.
_Avoid_: Dependency sweep, update check, bump bot

**Release PR**:
Pull request whose merge publishes one add-on version.
_Avoid_: Bump PR, update PR
