#!/usr/bin/env bash
# Startup module: load options, prepare the home, render config files, run as dev.

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

startup_authenticate_gh() {
  if ! bashio::var.has_value "${STARTUP_OPTIONS[github_token]}"; then
    return 0
  fi

  bashio::log.info "Authentification de la CLI gh"
  if printf '%s' "${STARTUP_OPTIONS[github_token]}" | startup_run_as_dev gh auth login --with-token; then
    if ! startup_run_as_dev gh auth setup-git; then
      bashio::log.warning "gh auth setup-git a échoué"
    fi
  else
    bashio::log.warning "gh auth login a échoué (token invalide ?)"
  fi
}

_startup_write_json() {
  local value="$1" destination="$2" mode="$3" label="$4"
  local message="$5" directory

  if ! bashio::var.has_value "${value}"; then
    return 0
  fi
  if ! printf '%s' "${value}" | jq -e . >/dev/null 2>&1; then
    bashio::log.warning "${label} ignoré : JSON invalide"
    return 0
  fi

  bashio::log.info "${message}"
  directory="$(dirname "${destination}")"
  mkdir -p "${directory}"
  printf '%s' "${value}" | jq . > "${destination}.tmp"
  chmod "${mode}" "${destination}.tmp"
  chown "${DEV_UID}:${DEV_GID}" "${destination}.tmp"
  mv "${destination}.tmp" "${destination}"
}

_startup_merge_json() {
  local value="$1" destination="$2" mode="$3" label="$4"
  local message="$5" directory incoming

  if ! bashio::var.has_value "${value}"; then
    return 0
  fi
  if ! printf '%s' "${value}" | jq -e . >/dev/null 2>&1; then
    bashio::log.warning "${label} ignoré : JSON invalide"
    return 0
  fi

  bashio::log.info "${message}"
  directory="$(dirname "${destination}")"
  mkdir -p "${directory}"
  incoming="${destination}.incoming"
  printf '%s' "${value}" | jq . > "${incoming}"
  if [ -f "${destination}" ]; then
    jq -s '.[0] * .[1]' "${destination}" "${incoming}" > "${destination}.tmp"
  else
    cp "${incoming}" "${destination}.tmp"
  fi
  chmod "${mode}" "${destination}.tmp"
  chown "${DEV_UID}:${DEV_GID}" "${destination}.tmp"
  mv "${destination}.tmp" "${destination}"
  rm -f "${incoming}"
}

startup_render_configs() {
  _startup_write_json \
    "${STARTUP_OPTIONS[opencode_config_json]}" \
    "${HOME_DIR}/.config/opencode/opencode.json" \
    644 \
    "opencode_config_json" \
    "Écriture de la configuration OpenCode"

  _startup_write_json \
    "${STARTUP_OPTIONS[opencode_auth_json]}" \
    "${HOME_DIR}/.local/share/opencode/auth.json" \
    600 \
    "opencode_auth_json" \
    "Écriture des identifiants OpenCode"

  _startup_merge_json \
    "${STARTUP_OPTIONS[t3_settings_json]}" \
    "${T3_HOME}/userdata/settings.json" \
    600 \
    "t3_settings_json" \
    "Fusion des réglages T3 Code (settings.json)"

  local directory
  for directory in "${HOME_DIR}/.config" "${HOME_DIR}/.local/share" "${T3_HOME}/userdata"; do
    if [ -d "${directory}" ]; then
      chown -R "${DEV_UID}:${DEV_GID}" "${directory}"
    fi
  done
}

startup_build_extra_env() {
  STARTUP_EXTRA_ENV=()
  if bashio::var.has_value "${STARTUP_OPTIONS[github_token]}"; then
    STARTUP_EXTRA_ENV+=("GH_TOKEN=${STARTUP_OPTIONS[github_token]}")
  fi
  while IFS=$'\t' read -r name value; do
    if [[ "${name}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      STARTUP_EXTRA_ENV+=("${name}=${value}")
    elif [ -n "${name}" ]; then
      bashio::log.warning "env_vars : nom ignoré (invalide) : ${name}"
    fi
  done < <(bashio::config 'env_vars' | jq -r '.[]? | [.name, .value] | @tsv' 2>/dev/null || true)
}

startup_exec_t3() {
  bashio::log.info "Démarrage de T3 Code sur ${T3_HOST}:${T3_PORT} (user ${DEV_USER}, workspace=${STARTUP_OPTIONS[workspace]})"

  _startup_build_dev_env
  exec env "${STARTUP_DEV_ENV[@]}" "${STARTUP_EXTRA_ENV[@]}" \
    s6-setuidgid "${DEV_USER}" \
    t3 serve \
      --mode web \
      --host "${T3_HOST}" \
      --port "${T3_PORT}" \
      --base-dir "${T3_HOME}" \
      --no-browser \
      --auto-bootstrap-project-from-cwd \
      "${STARTUP_OPTIONS[workspace]}"
}
