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
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl gnupg git jq ripgrep fd-find less vim nano zsh \
      sqlite3 xclip xsel wl-clipboard xvfb \
      build-essential python3 python3-pip python3-yaml unzip xz-utils \
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

ARG OPENCODE_VERSION=2.1.3
ARG T3_VERSION=0.1.0
ARG BUILD_VERSION

RUN npm install -g --omit=dev --no-audit --no-fund "@opencode/cli@${OPENCODE_VERSION}" "t3@${T3_VERSION}" \
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
      --arg addon "${BUILD_VERSION}" \
      '{opencode: $opencode, t3: $t3, addon: $addon}' \
      > /etc/t3-vibecoding/versions.json \
 && chmod 644 /etc/t3-vibecoding/versions.json

RUN groupadd -g 1000 dev \
 && useradd -u 1000 -g dev -m -s /bin/bash dev

COPY run.sh /
COPY lib/ /usr/local/lib/t3-vibecoding/
RUN chmod a+x /run.sh

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="aarch64|amd64"

CMD [ "/run.sh" ]
