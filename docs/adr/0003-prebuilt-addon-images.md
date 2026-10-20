# Publish pre-built add-on images instead of building on the device

Status: accepted

When `config.yaml` has no `image`, Home Assistant builds the add-on from its
`Dockerfile` on the user's device. This add-on installs Debian packages,
Node.js and two npm applications, so every install and update spends several
minutes building on the Home Assistant box; slower hardware such as a
Raspberry Pi makes it worse.

We publish a pre-built multi-architecture image to GitHub Container Registry and
set `image: "ghcr.io/ericcitaire/hass-t3-vibecoding"` in `config.yaml`. The
Supervisor then pulls the image tagged with the add-on `version` (it always uses
`version` as the tag) instead of building. CI builds `amd64` and `aarch64` on
native GitHub runners with the official Home Assistant builder actions, then
publishes one multi-arch manifest and signs it with Cosign.

## Considered Options

- Build on the device (status quo): rejected because of the install and update
  time, especially on ARM hardware where the npm packages are slow to install.
- Publish per-architecture images and use the `{arch}` placeholder: works, but
  the multi-arch manifest is the current recommendation and lets the Supervisor
  resolve the platform without the placeholder.
- Publish to Docker Hub: rejected because GHCR authenticates with the workflow's
  `GITHUB_TOKEN`, so no extra registry secret is needed.
- Use the legacy `home-assistant/builder` action: rejected because it is
  deprecated in favour of the composite BuildKit actions.

## Consequences

- A merge to `main` that touches `t3_vibecoding/` (or a manual dispatch)
  publishes the image for the `version` in `config.yaml`. Running the workflow
  again with an unchanged version rebuilds but does not overwrite published
  tags, so a release needs a version bump.
- The image must exist before a user installs or updates to that version. A
  failed workflow leaves the Supervisor unable to pull it.
- The GHCR package must be public, because Home Assistant pulls it anonymously.
  Package visibility is a one-time GitHub setting that the repository cannot
  guarantee.
- GitHub Container Registry stores every version tag and `latest`; old tags are
  kept until removed manually.
- The build workflow needs `packages: write` for GHCR and `id-token: write` for
  Cosign signing.
