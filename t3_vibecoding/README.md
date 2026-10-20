# T3 Code + OpenCode — Home Assistant add-on

Local Home Assistant OS add-on for **headless vibe coding**: it bundles the
developer tooling (`git`, `node`, `npm`, `ripgrep`, `fd`, `sqlite3`, `gh`,
build tools, `python3`), installs **OpenCode** and **T3 Code**, and starts `t3 serve`
automatically as a **non-root** user (`dev`).

- T3 Code web UI on `http://<host>:4096/` (pairing handled by T3).
- Integrated terminal and file editor from the T3 Code UI: no separate web IDE,
  port or password.
- Persistent state in `/data` (survives add-on updates).
- Default workspace: `/share/vibecoding` (HA `share` folder).
- Automatic restart on boot (`boot: auto`).

See [DOCS.md](DOCS.md) for installation, pairing and troubleshooting.

The add-on icon (`icon.png`) uses the
[T3 Code](https://github.com/pingdotgg/t3code) icon
(`assets/prod/black-universal-1024.png`, MIT license), resized to 128 × 128.
