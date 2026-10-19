#!/usr/bin/env bash
# Credentials module: one intake for secret files and child-process environment.

_credentials_write_json() {
  local value="$1" destination="$2" mode="$3" label="$4"
  local message="$5" directory

  if ! bashio::var.has_value "${value}"; then
    return 1
  fi
  if ! printf '%s' "${value}" | jq -e . >/dev/null 2>&1; then
    bashio::log.warning "${label} ignoré : JSON invalide"
    return 1
  fi

  bashio::log.info "${message}"
  directory="$(dirname "${destination}")"
  mkdir -p "${directory}"
  printf '%s' "${value}" | jq . > "${destination}.tmp"
  chmod "${mode}" "${destination}.tmp"
  chown "${DEV_UID}:${DEV_GID}" "${destination}.tmp"
  mv "${destination}.tmp" "${destination}"
}

_credentials_merge_json() {
  local value="$1" destination="$2" mode="$3" label="$4"
  local message="$5" directory incoming

  if ! bashio::var.has_value "${value}"; then
    return 1
  fi
  if ! printf '%s' "${value}" | jq -e . >/dev/null 2>&1; then
    bashio::log.warning "${label} ignoré : JSON invalide"
    return 1
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

credentials_authenticate_gh() {
  if ! bashio::var.has_value "${STARTUP_OPTIONS[github_token]}"; then
    return 1
  fi

  bashio::log.info "Authentification de la CLI gh"
  if printf '%s' "${STARTUP_OPTIONS[github_token]}" | startup_run_as_dev gh auth login --with-token; then
    if ! startup_run_as_dev gh auth setup-git; then
      bashio::log.warning "gh auth setup-git a échoué"
    fi
    return 0
  fi

  bashio::log.warning "gh auth login a échoué (token invalide ?)"
  return 1
}

credentials_apply() {
  local -a applied=()
  local directory

  if credentials_authenticate_gh; then
    applied+=("github")
  fi

  if _credentials_write_json \
    "${STARTUP_OPTIONS[opencode_config_json]}" \
    "${HOME_DIR}/.config/opencode/opencode.json" \
    644 \
    "opencode_config_json" \
    "Écriture de la configuration OpenCode"; then
    applied+=("opencode-config")
  fi

  if _credentials_write_json \
    "${STARTUP_OPTIONS[opencode_auth_json]}" \
    "${HOME_DIR}/.local/share/opencode/auth.json" \
    600 \
    "opencode_auth_json" \
    "Écriture des identifiants OpenCode"; then
    applied+=("opencode-auth")
  fi

  if _credentials_merge_json \
    "${STARTUP_OPTIONS[t3_settings_json]}" \
    "${T3_HOME}/userdata/settings.json" \
    600 \
    "t3_settings_json" \
    "Fusion des réglages T3 Code (settings.json)"; then
    applied+=("t3-settings")
  fi

  for directory in "${HOME_DIR}/.config" "${HOME_DIR}/.local/share" "${T3_HOME}/userdata"; do
    if [ -d "${directory}" ]; then
      chown -R "${DEV_UID}:${DEV_GID}" "${directory}"
    fi
  done

  if [ "${#applied[@]}" -gt 0 ]; then
    bashio::log.info "Identifiants/config appliqués : ${applied[*]}"
  fi
}

credentials_env() {
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
