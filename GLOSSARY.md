# T3 Code add-on

Home Assistant add-on that runs a headless T3 Code server with OpenCode and an
optional code-server.

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
