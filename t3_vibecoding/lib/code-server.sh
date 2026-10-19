#!/usr/bin/env bash
# code-server module: an s6 service owns preparation and supervision.

code_server_prepare() {
  local password="$1"
  local config_dir="${HOME_DIR}/.config/code-server"
  local data_dir="${HOME_DIR}/.local/share/code-server"
  local password_yaml

  if ! bashio::var.has_value "${password}"; then
    bashio::log.warning "code_server est activé mais code_server_password est vide : code-server ne démarrera pas"
    return 1
  fi

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
}

code_server_run() {
  local password

  startup_load_options
  startup_build_extra_env

  if ! bashio::config.true 'code_server'; then
    bashio::log.info "code-server désactivé"
    exec sleep infinity
  fi

  password="${STARTUP_OPTIONS[code_server_password]}"
  if ! code_server_prepare "${password}"; then
    exec sleep infinity
  fi

  bashio::log.info "Démarrage de code-server sur 0.0.0.0:${CODE_SERVER_PORT}"
  startup_exec_as_dev code-server --config "${HOME_DIR}/.config/code-server/config.yaml"
}
