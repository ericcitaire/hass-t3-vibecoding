ARG BUILD_FROM=ghcr.io/home-assistant/base-debian:trixie
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8

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

RUN npm install -g --omit=dev opencode-ai t3

RUN groupadd -g 1000 dev \
 && useradd -u 1000 -g dev -m -s /bin/bash dev

COPY run.sh /
RUN chmod a+x /run.sh

ARG BUILD_VERSION
ARG BUILD_ARCH
LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="aarch64|amd64"

CMD [ "/run.sh" ]
