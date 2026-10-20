# Install T3 preview browser system libraries in the add-on image

Status: accepted

T3 Code's `html_preview` and preview tabs need a server-side Chromium
(`chrome-headless-shell`). The add-on image did not provide the X11, GTK, NSS
and audio libraries that Chromium links against, so previews failed with
"This host is missing libraries T3's browser needs" even though T3 had
downloaded its browser into `/data/t3code/tools`.

We install the necessary Debian libraries and fonts in the image, mirroring the
`DEBIAN_PACKAGES` list from `t3 browser setup`, instead of asking the user to
run that command at runtime. The add-on has no `sudo` and no disposable root
shell, so a build-time install is the only reproducible option.

## Considered Options

- Run `t3 browser setup` on the Home Assistant host: rejected because the
  libraries must exist inside the container, not on the HAOS host, and the
  add-on user cannot install packages.
- Bake `chrome-headless-shell` into the image: rejected because `/data` is a
  runtime mount, so the browser would still have to be copied to the volume.
  T3 also pins and verifies its browser version, so a baked copy would often be
  ignored and downloaded again anyway. T3 downloads it once into the persistent
  volume instead.
- Install Playwright's full dependency list: rejected in favour of T3's own
  list, which is the supported set and less likely to grow the image with
  unused packages.

## Consequences

- The image grows by the Chromium runtime libraries plus fonts, in a headless
  add-on where that is otherwise surprising. The comment in the `Dockerfile`
  points at the source list to keep this from being removed as dead weight.
- The package list is tied to T3's internal `DEBIAN_PACKAGES` and Debian
  trixie's `t64` names; it must be re-checked when `T3_VERSION` changes.
- The browser binary itself is still downloaded at first preview. That is a
  deliberate trade-off: no image growth or version drift, at the cost of one
  network fetch into `/data` per browser version.
