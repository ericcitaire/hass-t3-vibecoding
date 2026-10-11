#!/usr/bin/with-contenv bashio
set -e

DEV_UID=1000
DEV_GID=1000
HOME_DIR="/data/home"
T3_HOME="/data/t3code"

T3_PORT="$(bashio::config 't3_port')"
T3_HOST="$(bashio::config 't3_host')"
WORKSPACE="$(bashio::config 'workspace')"
GIT_NAME="$(bashio::config 'git_name')"
GIT_EMAIL="$(bashio::config 'git_email')"

bashio::log.info "Préparation des répertoires persistants"
mkdir -p "${HOME_DIR}" "${T3_HOME}" "${WORKSPACE}"
chown -R "${DEV_UID}:${DEV_GID}" "${HOME_DIR}" "${T3_HOME}"
chown "${DEV_UID}:${DEV_GID}" "${WORKSPACE}"

if bashio::var.has_value "${GIT_NAME}"; then
  env HOME="${HOME_DIR}" s6-setuidgid dev git config --global user.name "${GIT_NAME}"
fi
if bashio::var.has_value "${GIT_EMAIL}"; then
  env HOME="${HOME_DIR}" s6-setuidgid dev git config --global user.email "${GIT_EMAIL}"
fi

env HOME="${HOME_DIR}" s6-setuidgid dev git config --global --add safe.directory "${WORKSPACE}"

bashio::log.info "Démarrage de T3 Code sur ${T3_HOST}:${T3_PORT} (user dev, workspace=${WORKSPACE})"

exec env \
  HOME="${HOME_DIR}" \
  T3CODE_HOME="${T3_HOME}" \
  XDG_CONFIG_HOME="${HOME_DIR}/.config" \
  XDG_DATA_HOME="${HOME_DIR}/.local/share" \
  XDG_CACHE_HOME="${HOME_DIR}/.cache" \
  TERM="xterm-256color" \
  PATH="/usr/local/bin:/usr/bin:/bin:${HOME_DIR}/.opencode/bin" \
  s6-setuidgid dev \
  t3 serve \
    --mode web \
    --host "${T3_HOST}" \
    --port "${T3_PORT}" \
    --base-dir "${T3_HOME}" \
    --no-browser \
    --auto-bootstrap-project-from-cwd \
    "${WORKSPACE}"
