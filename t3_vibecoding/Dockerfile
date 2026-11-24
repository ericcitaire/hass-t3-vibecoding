ARG BUILD_FROM=ghcr.io/home-assistant/base-debian:trixie
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8

# System libraries for T3 Code's headless preview browser live in
# browser-packages.txt so CI can compare them with `t3 browser setup`'s list.
# Fonts are required for pages to render correctly.
COPY browser-packages.txt /tmp/t3-browser-packages.txt

# OpenCode uses SQLite for `opencode db` and documents clipboard helpers for
# its TUI, including Xvfb for headless Linux.
# PDF tooling for real documents: `poppler-utils` provides the fast CLI
# extractors, `python3-pymupdf` extracts text and renders pages without the
# pypdf timeouts on large scans, `python3-pil` saves the rendered images and
# `python3-reportlab` generates new PDFs.
# They are Debian packages because the image's Python is externally managed:
# `pip install` fails without `--break-system-packages`.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl gnupg git jq ripgrep fd-find less vim nano bash-completion \
      sqlite3 xclip xsel wl-clipboard xvfb \
      build-essential python3 python3-pip python3-yaml unzip xz-utils \
      poppler-utils python3-pil python3-pymupdf python3-reportlab \
      procps openssh-client \
      $(cat /tmp/t3-browser-packages.txt) \
      fontconfig fonts-liberation fonts-dejavu-core \
 && rm -f /tmp/t3-browser-packages.txt \
 && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && mkdir -p -m 755 /etc/apt/keyrings \
 && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /etc/apt/keyrings/githubcli-archive-keyring.gpg \
 && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends gh \
 && ln -sf "$(command -v fdfind)" /usr/local/bin/fd \
 && rm -rf /var/lib/apt/lists/*

ARG OPENCODE_VERSION=2.3.0
ARG T3_VERSION=0.1.9
# Claude Code and Codex are the CLIs behind T3's `claudeAgent` and `codex`
# drivers; the GitHub Copilot CLI is for use from the integrated terminal.
ARG CLAUDE_CODE_VERSION=2.1.331
ARG CODEX_VERSION=0.172.0
ARG COPILOT_VERSION=1.0.115
ARG BUILD_VERSION

RUN npm install -g --omit=dev --no-audit --no-fund \
      "@opencode/cli@${OPENCODE_VERSION}" \
      "t3@${T3_VERSION}" \
      "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
      "@openai/codex@${CODEX_VERSION}" \
      "@github/copilot@${COPILOT_VERSION}" \
 && mv /usr/lib/node_modules/@opencode/cli/bin/opencode.exe /usr/lib/node_modules/@opencode/cli/bin/opencode.real \
 && printf '%s\n' \
      '#!/bin/sh' \
      'if [ "$#" -eq 1 ] && [ "$1" = "--version" ]; then' \
      '  /usr/bin/jq -r .version /usr/lib/node_modules/@opencode/cli/package.json' \
      '  exit 0' \
      'fi' \
      'exec /usr/lib/node_modules/@opencode/cli/bin/opencode.real "$@"' \
      > /usr/lib/node_modules/@opencode/cli/bin/opencode.exe \
 && chmod 755 /usr/lib/node_modules/@opencode/cli/bin/opencode.exe /usr/lib/node_modules/@opencode/cli/bin/opencode.real \
 && rm -rf /usr/lib/node_modules/@opencode/cli-linux-* \
 && npm cache clean --force \
 && rm -rf /root/.npm

RUN mkdir -p /etc/t3-vibecoding \
 && jq -n \
      --arg opencode "${OPENCODE_VERSION}" \
      --arg t3 "${T3_VERSION}" \
      --arg claude "${CLAUDE_CODE_VERSION}" \
      --arg codex "${CODEX_VERSION}" \
      --arg copilot "${COPILOT_VERSION}" \
      --arg addon "${BUILD_VERSION}" \
      '{opencode: $opencode, t3: $t3, claude: $claude, codex: $codex, copilot: $copilot, addon: $addon}' \
      > /etc/t3-vibecoding/versions.json \
 && chmod 644 /etc/t3-vibecoding/versions.json

# The npm and node installs above run as root and leave root-owned files in
# /tmp. Those ship inside the image, and the add-on only ever runs as dev, so
# clear them: /tmp/opencode, the scratch directory T3 Code points agents at,
# would otherwise be an empty directory the agent cannot write to.
RUN groupadd -g 1000 dev \
 && useradd -u 1000 -g dev -m -s /bin/bash dev \
 && rm -rf /tmp/opencode /tmp/node-compile-cache /tmp/.bun-* \
 && install -d -o dev -g dev -m 0755 /tmp/opencode

COPY run.sh /
COPY lib/ /usr/local/lib/t3-vibecoding/
# The shell setup is appended to Debian's /etc/bash.bashrc instead of replacing
# it, so Debian's locale and completion defaults keep working. A user's own
# ~/.bashrc is sourced after it and still wins.
COPY bashrc /tmp/t3-vibecoding-bashrc
RUN chmod a+x /run.sh \
 && cat /tmp/t3-vibecoding-bashrc >> /etc/bash.bashrc \
 && rm -f /tmp/t3-vibecoding-bashrc

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="aarch64|amd64"

CMD [ "/run.sh" ]
