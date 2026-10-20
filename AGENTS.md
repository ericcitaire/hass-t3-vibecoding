## Language

Reply to me in French. Everything committed to this repository — code, commits, and Markdown documentation — is in English. French is reserved for interactions between agents and me.

## Conventions

Keep add-on release metadata coherent: `version` in `t3_vibecoding/config.yaml`, the top entry in `t3_vibecoding/CHANGELOG.md`, and the component versions quoted in `t3_vibecoding/DOCS.md` must match the `ARG` defaults in `t3_vibecoding/Dockerfile`.

## Workspaces

- The root checkout (`/data/home/hass-t3-vibecoding`) stays on `main` and is only used for integration: no work branches, no feature commits. Only merges into `main` happen there.
- Each task runs in a dedicated worktree created from `main`, never by creating a branch in the root: otherwise two threads diverge in the same checkout and the next one inherits the wrong state.
- One branch per thread. After merging into `main`, remove the worktree and its branch.
- Only one thread merges into `main`; the others hand their branch back. T3 records the branch at launch: switching branches in the root makes its metadata wrong.

## Agent skills

### Issue tracker

Issues live in GitHub Issues on `ericcitaire/hass-t3-vibecoding`, managed with `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
