#!/usr/bin/env bash
# Credentials module: one intake for secret files and child-process environment.

# Settings applied on every start for keys the user has not chosen. T3 Code's
# "Keep awake while agents work" spawns systemd-inhibit, which talks to
# systemd-logind over the system bus: the add-on container has neither, so the
# helper fails with ENOENT and retries with an exponential backoff, logging
# "keep-awake sleep inhibitor stopped" during every run. The setting is
# useless here, so it defaults to off; the UI or t3_settings_json can turn it
# back on.
T3_DEFAULT_SETTINGS='{"keepAwakeWhileAgentsWork":false}'

_credentials_write_json() {
  local value="$1" destination="$2" mode="$3" label="$4"
  local message="$5" directory

  if ! bashio::var.has_value "${value}"; then
    return 1
  fi
  if ! printf '%s' "${value}" | jq -e . >/dev/null 2>&1; then
    bashio::log.warning "${label} ignored: invalid JSON"
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
  local message="$5" merge="${6:-.[0] * .[1]}" directory incoming

  if ! bashio::var.has_value "${value}"; then
    return 1
  fi
  if ! printf '%s' "${value}" | jq -e . >/dev/null 2>&1; then
    bashio::log.warning "${label} ignored: invalid JSON"
    return 1
  fi

  bashio::log.info "${message}"
  directory="$(dirname "${destination}")"
  mkdir -p "${directory}"
  incoming="${destination}.incoming"
  printf '%s' "${value}" | jq . > "${incoming}"
  if [ -f "${destination}" ]; then
    jq -s "${merge}" "${destination}" "${incoming}" > "${destination}.tmp"
  else
    cp "${incoming}" "${destination}.tmp"
  fi
  chmod "${mode}" "${destination}.tmp"
  chown "${DEV_UID}:${DEV_GID}" "${destination}.tmp"
  mv "${destination}.tmp" "${destination}"
  rm -f "${incoming}"
}

# Merges defaults: unlike _credentials_merge_json, keys already set in the
# destination win, so a setting the user changed in the T3 Code UI survives
# every restart.
_credentials_merge_defaults() {
  _credentials_merge_json "$1" "$2" "$3" "$4" "$5" '.[1] * .[0]'
}

credentials_authenticate_gh() {
  if ! bashio::var.has_value "${STARTUP_OPTIONS[github_token]}"; then
    return 1
  fi

  bashio::log.info "Authenticating the gh CLI"
  if printf '%s' "${STARTUP_OPTIONS[github_token]}" | startup_run_as_dev gh auth login --with-token; then
    if ! startup_run_as_dev gh auth setup-git; then
      bashio::log.warning "gh auth setup-git failed"
    fi
    return 0
  fi

  bashio::log.warning "gh auth login failed (invalid token?)"
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
    "Writing OpenCode configuration"; then
    applied+=("opencode-config")
  fi

  if _credentials_write_json \
    "${STARTUP_OPTIONS[opencode_auth_json]}" \
    "${HOME_DIR}/.local/share/opencode/auth.json" \
    600 \
    "opencode_auth_json" \
    "Writing OpenCode credentials"; then
    applied+=("opencode-auth")
  fi

  if _credentials_merge_defaults \
    "${T3_DEFAULT_SETTINGS}" \
    "${T3_HOME}/userdata/settings.json" \
    600 \
    "T3 Code defaults" \
    "Applying T3 Code defaults (settings.json)"; then
    applied+=("t3-defaults")
  fi

  if _credentials_merge_json \
    "${STARTUP_OPTIONS[t3_settings_json]}" \
    "${T3_HOME}/userdata/settings.json" \
    600 \
    "t3_settings_json" \
    "Merging T3 Code settings (settings.json)"; then
    applied+=("t3-settings")
  fi

  for directory in "${HOME_DIR}/.config" "${HOME_DIR}/.local/share" "${T3_HOME}/userdata"; do
    if [ -d "${directory}" ]; then
      chown -R "${DEV_UID}:${DEV_GID}" "${directory}"
    fi
  done

  if [ "${#applied[@]}" -gt 0 ]; then
    bashio::log.info "Applied credentials/config: ${applied[*]}"
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
      bashio::log.warning "env_vars: ignoring invalid name: ${name}"
    fi
  done < <(bashio::config 'env_vars' | jq -r '.[]? | [.name, .value] | @tsv' 2>/dev/null || true)
}
