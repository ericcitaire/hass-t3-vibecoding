# Run the dependency sweep from GitHub Actions instead of a dependency bot

Status: accepted

The image pins three upstream projects in the `Dockerfile`
(`OPENCODE_VERSION`, `T3_VERSION`, `POWERLEVEL10K_VERSION`) and sits on the
floating `base-debian:trixie` tag. Refreshing them was a documented manual
procedure: look the versions up on npm, edit the build args, bump `version`,
write the CHANGELOG entry, merge. In practice releases were forgotten, so users
ran months-old OpenCode and T3 builds, and the built-in `t3 update` path is not
an option (updates inside the container are lost on the next image build).

The hard part is not noticing that a version moved: it is that a release is one
atomic change across four surfaces — the build args, `version` in `config.yaml`
(which is also the image tag the Supervisor pulls), the top `CHANGELOG.md`
entry, and the versions quoted in `DOCS.md`. Splitting that across several pull
requests, or leaving one of them to a human step, reintroduces the drift the
sweep is meant to remove.

We added `.github/workflows/dependency-sweep.yml`, backed by
`scripts/dependency-sweep.py` and the shared `scripts/addon_versions.py`:

- a weekly schedule compares pinned versions with npm's `latest` dist-tag and
  with the newest GitHub tag, and a monthly schedule also publishes a package
  refresh so Debian and `apt` security fixes reach the image;
- when something moved, the workflow produces one commit on
  `chore/dependency-sweep` — build args, `version`, CHANGELOG entry, DOCS
  quotes — runs the full `Verify add-on` suite on that branch, then opens or
  refreshes a single PR. Merging it is the release.

## Considered Options

- **Dependabot**: rejected on facts, not preference. Its `docker` ecosystem only
  parses `FROM` lines, so it cannot see the three build args that carry the
  components; it has no manager for arbitrary files, so it can never write
  `config.yaml`, the CHANGELOG or `DOCS.md`. It would watch the base image tag
  and the Actions pins, which are not what breaks.
- **Renovate, hosted app**: it can read the build args through a regex custom
  manager and group the updates, but it does not know what an "add-on version"
  is, so the release half stays custom. Making a bot commit land on the
  Renovate branch would also need a push token, because a `GITHUB_TOKEN` push
  does not retrigger CI — the release commit would go unverified.
- **Renovate, self-hosted**: `postUpgradeTasks` would let a script write the
  release surfaces in the same PR, but that requires a self-hosted runner
  configuration, a push token, and the same release script. It costs more
  moving parts than it removes, for three dependencies.
- **Release tooling driven by commits** (`release-please`, `semantic-release`):
  rejected because the version lives in `config.yaml` rather than a manifest,
  and because agent-authored commits are not consistently conventional.

## Consequences

- The release is one commit and one PR; `version`, the CHANGELOG and `DOCS.md`
  can no longer disagree by construction, and `scripts/verify-versions.py`
  enforces it on every pull request.
- The release PR is opened with `GITHUB_TOKEN`, so it does not trigger
  `pull_request` workflows. `verify.yml` therefore exposes `workflow_call` and
  the sweep runs it on the release branch before opening the PR; the PR body
  records the result. As a consequence, the PR does not show GitHub's own check
  runs.
- The sweep needs the repository setting **Allow GitHub Actions to create and
  approve pull requests**. It fails, visibly, at the last step when disabled.
- The CHANGELOG entry is generated as a skeleton (one bullet per bump plus
  release links); the maintainer enriches it in the PR when a bump deserves
  prose. A leftover `TODO` fails the metadata check.
- The add-on version follows the upstream change: an upstream major or minor
  release opens an add-on minor release, an upstream patch stays a patch, and a
  package refresh is a patch.
- The floating base image tag is reported by the sweep but never triggers a
  bump: it has no comparable version, and updates arrive with any rebuild.
- GHCR keeps every version tag; old ones are still removed by hand.
