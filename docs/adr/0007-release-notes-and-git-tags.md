# Publish real releases from a staged Unreleased section

Status: accepted

The add-on is published as an image tagged with `version` from `config.yaml`.
Until now that image tag was the only release artefact: there were no Git tags
and no GitHub Releases. The CHANGELOG was written by the dependency sweep from
component bumps alone, so a feature or fix merged between two sweeps never
appeared in any entry. PR #13 (PDF tooling) is the concrete case: merged, built,
and absent from the notes because it did not bump `version`.

ADR 0005 made the release PR the only place where the four release surfaces
move. That part stays. What was missing is where a non-dependency change is
recorded *before* the release, and what marks a release once its image is
published.

## Decision

`t3_vibecoding/CHANGELOG.md` carries a permanent `## Unreleased` section at the
top, with three subsections: `### Added`, `### Changed` and `### Fixed`.

- Every pull request that changes a user-visible path adds one bullet there, in
  the same pull request. Documentation-, CI- and test-only pull requests are
  exempt; the `skip-changelog` label opts an internal change out.
- A CI gate (`scripts/verify-changelog.py`) fails a pull request that touches
  `Dockerfile`, `run.sh`, `lib/`, `services/`, `config.yaml`, `translations/`
  or `browser-packages.txt` without a new Unreleased bullet.
- The release workflow folds `## Unreleased` into the new version entry and
  leaves the section empty. The sweep's component bullets follow under
  `### Bundled components`.
- The bump follows the staged sections: `Added` or `Changed` opens a minor
  release, `Fixed` alone is a patch, and a dependency-only release follows the
  upstream bump as before. `workflow_dispatch` can override the kind.
- Releases are still cut by one PR that is merged by hand. The weekly schedule
  releases when a component moved or `Unreleased` has content; the monthly
  schedule still produces a package refresh. A manual run can force a release
  with `release_now`.
- After the multi-arch manifest is published, the build workflow creates an
  annotated tag `v<version>` on the release commit and a GitHub Release whose
  body is the CHANGELOG entry for that version, prefixed by the image name and
  architectures. The job only acts when the push bumped `version`, so a
  documentation push that rebuilds an already published image never backfills
  an old entry. No historical tag is backfilled.

## Considered Options

- **Generate the notes from Git history** with release-please, git-cliff or
  GitHub's generate-notes API. Rejected after weighing them: release-please
  would become a second release manager and creates its tag and Release before
  the image build; git-cliff reads commit messages rather than the curated
  prose authors already write in pull requests; generate-notes needs a label on
  every pull request and produces title lists. A staged section keeps the
  author's context and needs no new tool.
- **Write the section at release time from merged pull requests.** Rejected:
  the maintainer would reconstruct what each PR meant days later, which is the
  failure mode that hid #13 in the first place.
- **Auto-merge the release PR** when the notes are machine-generated. With a
  hand-written section there is prose to review, and the image is not
  smoke-tested before publication; the merge stays manual.
- **Backfill tags and Releases for 0.15.0 and 0.15.1.** Rejected: released
  entries are not rewritten, and the tag is no longer needed to compute a note
  range.

## Consequences

- The next release is **0.16.0**, because the seeded Unreleased bullet for #13
  is an addition.
- Changes merged before this convention stay absent from published entries:
  #10 (`/tmp/opencode` writable by `dev`) shipped in 0.15.1 without a note, and
  released entries are not rewritten.
- The release PR can no longer leave the CHANGELOG empty; `verify-versions.py`
  rejects a missing or malformed `## Unreleased`, unknown sections, and
  placeholders.
- The changelog gate runs on `pull_request` only. The release branch is
  verified through `workflow_call`, where the gate is skipped because the
  release PR intentionally drains the section.
- The build workflow needs `contents: write` on its release job, and the
  Release is created only after the multi-arch manifest succeeds, so a failed
  or partial build never announces a release. The job also requires the push to
  change `version`, so merging a documentation-only change cannot tag the tip
  of `main` with an already published version. An existing tag or Release is
  left alone.
- The GitHub Release body and the CHANGELOG cannot drift: `changelog-entry.py`
  prints the top entry and the build workflow uses it verbatim.
