#!/usr/bin/env bash
# Startup module: load options, prepare the home, run child processes as dev.

DEV_UID=1000
DEV_GID=1000
DEV_USER="dev"
HOME_DIR="/data/home"
T3_HOME="/data/t3code"
T3_PORT=4096
T3_HOST="0.0.0.0"
VERSIONS_FILE="${VERSIONS_FILE:-/etc/t3-vibecoding/versions.json}"
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
}

_startup_build_dev_env() {
  STARTUP_DEV_ENV=(
    "HOME=${HOME_DIR}"
    "T3CODE_HOME=${T3_HOME}"
    "XDG_CONFIG_HOME=${HOME_DIR}/.config"
    "XDG_DATA_HOME=${HOME_DIR}/.local/share"
    "XDG_CACHE_HOME=${HOME_DIR}/.cache"
    "TERM=xterm-256color"
    # T3 opens the integrated terminal with $SHELL (and hydrates PATH through
    # it), so this is what makes zsh with powerlevel10k the default.
    "SHELL=/bin/zsh"
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

  bashio::log.info "Preparing persistent directories"
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
  local opencode_version="unknown"
  local t3_cli_version="unknown"

  if [ -r "${VERSIONS_FILE}" ]; then
    opencode_version="$(jq -r '.opencode // "unknown"' "${VERSIONS_FILE}")"
    t3_cli_version="$(jq -r '.t3 // "unknown"' "${VERSIONS_FILE}")"
  else
    bashio::log.warning "Version stamp missing: ${VERSIONS_FILE}"
  fi

  bashio::log.info "Bundled versions: opencode ${opencode_version}, t3 ${t3_cli_version}"
}

startup_exec_t3() {
  bashio::log.info "Starting T3 Code on ${T3_HOST}:${T3_PORT} (user ${DEV_USER}, workspace=${STARTUP_OPTIONS[workspace]})"

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
