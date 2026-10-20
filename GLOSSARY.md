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
