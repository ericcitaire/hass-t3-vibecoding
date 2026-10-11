#!/usr/bin/with-contenv bashio
set -e

DEV_UID=1000
DEV_GID=1000
DEV_USER="dev"
HOME_DIR="/data/home"
T3_HOME="/data/t3code"

T3_PORT="$(bashio::config 't3_port')"
T3_HOST="$(bashio::config 't3_host')"
WORKSPACE="$(bashio::config 'workspace')"
GIT_NAME="$(bashio::config 'git_name')"
GIT_EMAIL="$(bashio::config 'git_email')"
GITHUB_TOKEN="$(bashio::config 'github_token')"
OPENCODE_CONFIG_JSON="$(bashio::config 'opencode_config_json')"
OPENCODE_AUTH_JSON="$(bashio::config 'opencode_auth_json')"
T3_SETTINGS_JSON="$(bashio::config 't3_settings_json')"

bashio::log.info "Préparation des répertoires persistants"
mkdir -p "${HOME_DIR}" "${T3_HOME}" "${WORKSPACE}"
chown -R "${DEV_UID}:${DEV_GID}" "${HOME_DIR}" "${T3_HOME}"
chown "${DEV_UID}:${DEV_GID}" "${WORKSPACE}"

if bashio::var.has_value "${GIT_NAME}"; then
  env HOME="${HOME_DIR}" s6-setuidgid "${DEV_USER}" git config --global user.name "${GIT_NAME}"
fi
if bashio::var.has_value "${GIT_EMAIL}"; then
  env HOME="${HOME_DIR}" s6-setuidgid "${DEV_USER}" git config --global user.email "${GIT_EMAIL}"
fi
env HOME="${HOME_DIR}" s6-setuidgid "${DEV_USER}" git config --global --add safe.directory "${WORKSPACE}"

if bashio::var.has_value "${GITHUB_TOKEN}"; then
  bashio::log.info "Authentification de la CLI gh"
  if printf '%s' "${GITHUB_TOKEN}" | env HOME="${HOME_DIR}" s6-setuidgid "${DEV_USER}" gh auth login --with-token; then
    env HOME="${HOME_DIR}" s6-setuidgid "${DEV_USER}" gh auth setup-git || true
  else
    bashio::log.warning "gh auth login a échoué (token invalide ?)"
  fi
fi

if bashio::var.has_value "${OPENCODE_CONFIG_JSON}"; then
  if printf '%s' "${OPENCODE_CONFIG_JSON}" | jq -e . >/dev/null 2>&1; then
    bashio::log.info "Écriture de la configuration OpenCode"
    mkdir -p "${HOME_DIR}/.config/opencode"
    printf '%s' "${OPENCODE_CONFIG_JSON}" | jq . > "${HOME_DIR}/.config/opencode/opencode.json"
    chown -R "${DEV_UID}:${DEV_GID}" "${HOME_DIR}/.config"
  else
    bashio::log.warning "opencode_config_json ignoré : JSON invalide"
  fi
fi

if bashio::var.has_value "${OPENCODE_AUTH_JSON}"; then
  if printf '%s' "${OPENCODE_AUTH_JSON}" | jq -e . >/dev/null 2>&1; then
    bashio::log.info "Écriture des identifiants OpenCode"
    mkdir -p "${HOME_DIR}/.local/share/opencode"
    printf '%s' "${OPENCODE_AUTH_JSON}" | jq . > "${HOME_DIR}/.local/share/opencode/auth.json"
    chmod 600 "${HOME_DIR}/.local/share/opencode/auth.json"
    chown -R "${DEV_UID}:${DEV_GID}" "${HOME_DIR}/.local/share"
  else
    bashio::log.warning "opencode_auth_json ignoré : JSON invalide"
  fi
fi

if bashio::var.has_value "${T3_SETTINGS_JSON}"; then
  if printf '%s' "${T3_SETTINGS_JSON}" | jq -e . >/dev/null 2>&1; then
    bashio::log.info "Fusion des réglages T3 Code (settings.json)"
    SETTINGS_PATH="${T3_HOME}/userdata/settings.json"
    mkdir -p "${T3_HOME}/userdata"
    printf '%s' "${T3_SETTINGS_JSON}" | jq . > "${T3_HOME}/userdata/settings.incoming.json"
    if [ -f "${SETTINGS_PATH}" ]; then
      jq -s '.[0] * .[1]' "${SETTINGS_PATH}" "${T3_HOME}/userdata/settings.incoming.json" > "${SETTINGS_PATH}.tmp"
    else
      cp "${T3_HOME}/userdata/settings.incoming.json" "${SETTINGS_PATH}.tmp"
    fi
    mv "${SETTINGS_PATH}.tmp" "${SETTINGS_PATH}"
    rm -f "${T3_HOME}/userdata/settings.incoming.json"
    chown "${DEV_UID}:${DEV_GID}" "${SETTINGS_PATH}"
    chmod 600 "${SETTINGS_PATH}"
  else
    bashio::log.warning "t3_settings_json ignoré : JSON invalide"
  fi
fi

declare -a EXTRA_ENV=()
if bashio::var.has_value "${GITHUB_TOKEN}"; then
  EXTRA_ENV+=("GH_TOKEN=${GITHUB_TOKEN}")
fi
while IFS=$'\t' read -r name value; do
  if [[ "${name}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    EXTRA_ENV+=("${name}=${value}")
  elif [ -n "${name}" ]; then
    bashio::log.warning "env_vars : nom ignoré (invalide) : ${name}"
  fi
done < <(bashio::config 'env_vars' | jq -r '.[]? | [.name, .value] | @tsv' 2>/dev/null || true)

bashio::log.info "Démarrage de T3 Code sur ${T3_HOST}:${T3_PORT} (user ${DEV_USER}, workspace=${WORKSPACE})"

exec env "${EXTRA_ENV[@]}" \
  HOME="${HOME_DIR}" \
  T3CODE_HOME="${T3_HOME}" \
  XDG_CONFIG_HOME="${HOME_DIR}/.config" \
  XDG_DATA_HOME="${HOME_DIR}/.local/share" \
  XDG_CACHE_HOME="${HOME_DIR}/.cache" \
  TERM="xterm-256color" \
  PATH="/usr/local/bin:/usr/bin:/bin:${HOME_DIR}/.opencode/bin" \
  s6-setuidgid "${DEV_USER}" \
  t3 serve \
    --mode web \
    --host "${T3_HOST}" \
    --port "${T3_PORT}" \
    --base-dir "${T3_HOME}" \
    --no-browser \
    --auto-bootstrap-project-from-cwd \
    "${WORKSPACE}"
