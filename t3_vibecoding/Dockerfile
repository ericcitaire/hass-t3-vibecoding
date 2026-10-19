ARG BUILD_FROM=ghcr.io/home-assistant/base-debian:trixie
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8

ARG BUILD_ARCH
ARG CODE_SERVER_VERSION=4.141.0

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl gnupg git jq ripgrep fd-find less vim nano \
      build-essential python3 unzip xz-utils procps openssh-client \
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

RUN set -eux; \
    case "${BUILD_ARCH:-$(dpkg --print-architecture)}" in \
      amd64) cs_arch="amd64" ;; \
      arm64|aarch64) cs_arch="arm64" ;; \
      *) echo "Architecture non supportée pour code-server : ${BUILD_ARCH:-$(dpkg --print-architecture)}" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/coder/code-server/releases/download/v${CODE_SERVER_VERSION}/code-server-${CODE_SERVER_VERSION}-linux-${cs_arch}.tar.gz" \
      -o /tmp/code-server.tar.gz; \
    mkdir -p /usr/local/lib; \
    tar -xzf /tmp/code-server.tar.gz -C /usr/local/lib; \
    mv "/usr/local/lib/code-server-${CODE_SERVER_VERSION}-linux-${cs_arch}" /usr/local/lib/code-server; \
    ln -sf /usr/local/lib/code-server/bin/code-server /usr/local/bin/code-server; \
    rm -f /tmp/code-server.tar.gz

ARG OPENCODE_VERSION=1.19.3
ARG T3_VERSION=0.1.0

RUN npm install -g --omit=dev "opencode-ai@${OPENCODE_VERSION}" "t3@${T3_VERSION}"

RUN mv /usr/lib/node_modules/opencode-ai/bin/opencode.exe /usr/lib/node_modules/opencode-ai/bin/opencode.real \
 && printf '%s\n' \
      '#!/bin/sh' \
      'if [ "$#" -eq 1 ] && [ "$1" = "--version" ]; then' \
      '  /usr/bin/jq -r .version /usr/lib/node_modules/opencode-ai/package.json' \
      '  exit 0' \
      'fi' \
      'exec /usr/lib/node_modules/opencode-ai/bin/opencode.real "$@"' \
      > /usr/lib/node_modules/opencode-ai/bin/opencode.exe \
 && chmod 755 /usr/lib/node_modules/opencode-ai/bin/opencode.exe /usr/lib/node_modules/opencode-ai/bin/opencode.real

RUN groupadd -g 1000 dev \
 && useradd -u 1000 -g dev -m -s /bin/bash dev

COPY run.sh /
COPY lib/ /usr/local/lib/t3-vibecoding/
COPY services/ /etc/services.d/
RUN chmod a+x /run.sh /etc/services.d/code-server/run

ARG BUILD_VERSION
LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="aarch64|amd64"

CMD [ "/run.sh" ]
