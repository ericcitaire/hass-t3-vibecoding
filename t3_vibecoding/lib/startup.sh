#!/usr/bin/env bash
# Startup module: load options, prepare the home, run child processes as dev.

DEV_UID=1000
DEV_GID=1000
DEV_USER="dev"
HOME_DIR="/data/home"
T3_HOME="/data/t3code"
T3_PORT=4096
T3_HOST="0.0.0.0"
CODE_SERVER_PORT=8081
STARTUP_PATH="${STARTUP_PATH:-/usr/local/bin:/usr/bin:/bin:${HOME_DIR}/.opencode/bin}"

declare -A STARTUP_OPTIONS=()
declare -a STARTUP_EXTRA_ENV=()
declare -a STARTUP_DEV_ENV=()

startup_load_options() {
  STARTUP_OPTIONS[workspace]="$(bashio::config 'workspace')"
  STARTUP_OPTIONS[git_name]="$(bashio::config 'git_name')"
  STARTUP_OPTIONS[git_email]="$(bashio::config 'git_email')"
  STARTUP_OPTIONS[github_token]="$(bashio::config 'github_token')"
  STARTUP_OPTIONS[opencode_config_json]="$(bashio::config 'opencode_config_json')"
  STARTUP_OPTIONS[opencode_auth_json]="$(bashio::config 'opencode_auth_json')"
  STARTUP_OPTIONS[t3_settings_json]="$(bashio::config 't3_settings_json')"
  STARTUP_OPTIONS[code_server_password]="$(bashio::config 'code_server_password')"
}

_startup_build_dev_env() {
  STARTUP_DEV_ENV=(
    "HOME=${HOME_DIR}"
    "T3CODE_HOME=${T3_HOME}"
    "XDG_CONFIG_HOME=${HOME_DIR}/.config"
    "XDG_DATA_HOME=${HOME_DIR}/.local/share"
    "XDG_CACHE_HOME=${HOME_DIR}/.cache"
    "TERM=xterm-256color"
    "PATH=${STARTUP_PATH}"
  )
}

startup_run_as_dev() {
  _startup_build_dev_env
  env "${STARTUP_DEV_ENV[@]}" "${STARTUP_EXTRA_ENV[@]}" s6-setuidgid "${DEV_USER}" "$@"
}

startup_exec_as_dev() {
  _startup_build_dev_env
  exec env "${STARTUP_DEV_ENV[@]}" "${STARTUP_EXTRA_ENV[@]}" s6-setuidgid "${DEV_USER}" "$@"
}

startup_prepare_home() {
  local workspace="${STARTUP_OPTIONS[workspace]}"

  bashio::log.info "Préparation des répertoires persistants"
  mkdir -p "${HOME_DIR}" "${T3_HOME}" "${workspace}"
  chown -R "${DEV_UID}:${DEV_GID}" "${HOME_DIR}" "${T3_HOME}"
  chown "${DEV_UID}:${DEV_GID}" "${workspace}"

  if bashio::var.has_value "${STARTUP_OPTIONS[git_name]}"; then
    startup_run_as_dev git config --global user.name "${STARTUP_OPTIONS[git_name]}"
  fi
  if bashio::var.has_value "${STARTUP_OPTIONS[git_email]}"; then
    startup_run_as_dev git config --global user.email "${STARTUP_OPTIONS[git_email]}"
  fi
  startup_run_as_dev git config --global --add safe.directory "${workspace}"
}

startup_log_versions() {
  local opencode_version t3_cli_version code_server_version version_tmp

  opencode_version="$(startup_run_as_dev opencode --version 2>/dev/null || echo 'inconnu')"
  t3_cli_version="$(startup_run_as_dev t3 --version 2>/dev/null || echo 'inconnu')"
  version_tmp="$(mktemp -d)"
  chown "${DEV_UID}:${DEV_GID}" "${version_tmp}"
  code_server_version="$(
    env HOME="${HOME_DIR}" \
      XDG_CONFIG_HOME="${version_tmp}/config" \
      XDG_DATA_HOME="${version_tmp}/data" \
      PATH="${STARTUP_PATH}" \
      s6-setuidgid "${DEV_USER}" \
      code-server --version 2>/dev/null | head -n1 || echo 'inconnue'
  )"
  rm -rf "${version_tmp}"

  bashio::log.info "Versions embarquées : opencode ${opencode_version}, t3 ${t3_cli_version}, code-server ${code_server_version}"
}

startup_exec_t3() {
  bashio::log.info "Démarrage de T3 Code sur ${T3_HOST}:${T3_PORT} (user ${DEV_USER}, workspace=${STARTUP_OPTIONS[workspace]})"

  startup_exec_as_dev \
    t3 serve \
      --mode web \
      --host "${T3_HOST}" \
      --port "${T3_PORT}" \
      --base-dir "${T3_HOME}" \
      --no-browser \
      --auto-bootstrap-project-from-cwd \
      "${STARTUP_OPTIONS[workspace]}"
}
