#!/usr/bin/with-contenv bashio
set -e

# shellcheck source=/dev/null
source /usr/local/lib/t3-vibecoding/startup.sh

startup_load_options
startup_prepare_home
startup_build_extra_env
startup_log_versions
startup_authenticate_gh
startup_render_configs

start_code_server() {
  if ! bashio::config.true 'code_server'; then
    bashio::log.info "code-server désactivé"
    return 0
  fi

  local password="${STARTUP_OPTIONS[code_server_password]}"
  if ! bashio::var.has_value "${password}"; then
    bashio::log.warning "code_server est activé mais code_server_password est vide : code-server ne démarrera pas"
    return 0
  fi

  local config_dir="${HOME_DIR}/.config/code-server"
  local data_dir="${HOME_DIR}/.local/share/code-server"

  if ! (
    set -e
    local password_yaml
    mkdir -p "${config_dir}" "${data_dir}"
    password_yaml="$(jq -Rn --arg p "${password}" '$p')"
    cat > "${config_dir}/config.yaml" <<EOF
bind-addr: 0.0.0.0:${CODE_SERVER_PORT}
auth: password
password: ${password_yaml}
cert: false
disable-telemetry: true
disable-update-check: true
EOF
    chmod 600 "${config_dir}/config.yaml"
    chown -R "${DEV_UID}:${DEV_GID}" "${config_dir}" "${data_dir}"
  ); then
    bashio::log.warning "Impossible de préparer la configuration de code-server"
    return 0
  fi

  bashio::log.info "Démarrage de code-server sur 0.0.0.0:${CODE_SERVER_PORT}"
  (
    while true; do
      startup_run_as_dev code-server --config "${config_dir}/config.yaml" \
        || bashio::log.warning "code-server s'est arrêté, redémarrage dans 5 secondes"
      sleep 5
    done
  ) &
}

start_code_server

startup_exec_t3
