#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "${ROOT}/t3_vibecoding/lib/startup.sh"

TEST_TMP="$(mktemp -d)"
trap 'rm -rf "${TEST_TMP}"' EXIT
STUB_DIR="${TEST_TMP}/bin"
mkdir -p "${STUB_DIR}"

HOME_DIR="${TEST_TMP}/home"
T3_HOME="${TEST_TMP}/t3code"
STARTUP_PATH="${STUB_DIR}:/usr/bin:/bin"

cat > "${STUB_DIR}/s6-setuidgid" <<'EOF'
#!/usr/bin/env bash
shift
exec "$@"
EOF

cat > "${STUB_DIR}/git" <<EOF
#!/usr/bin/env bash
printf 'git %s\n' "\$*" >> "${TEST_TMP}/git.log"
EOF

cat > "${STUB_DIR}/gh" <<EOF
#!/usr/bin/env bash
cat >/dev/null || true
printf 'gh %s\n' "\$*" >> "${TEST_TMP}/gh.log"
EOF

cat > "${STUB_DIR}/opencode" <<'EOF'
#!/usr/bin/env bash
printf '1.19.3\n'
EOF

cat > "${STUB_DIR}/t3" <<'EOF'
#!/usr/bin/env bash
printf '0.1.0\n'
EOF

cat > "${STUB_DIR}/code-server" <<'EOF'
#!/usr/bin/env bash
printf '4.141.0\n'
EOF

chmod +x "${STUB_DIR}"/*

declare -A CONFIG_VALUES=()

bashio::config() {
  printf '%s' "${CONFIG_VALUES[$1]:-}"
}

bashio::var.has_value() {
  [ -n "${1:-}" ]
}

bashio::config.true() {
  [ "${CONFIG_VALUES[$1]:-false}" = "true" ]
}

bashio::log.info() { :; }
bashio::log.warning() { printf 'WARN: %s\n' "$*" >&2; }
chown() { :; }

TESTS_RUN=0
TESTS_FAILED=0
CURRENT_TEST=""

fail() {
  printf 'FAIL %s: %s\n' "${CURRENT_TEST}" "$*" >&2
  exit 1
}

assert_eq() {
  [ "$1" = "$2" ] || fail "expected [$2], got [$1]"
}

assert_file() {
  [ -f "$1" ] || fail "missing file $1"
}

assert_no_file() {
  [ ! -e "$1" ] || fail "unexpected file $1"
}

assert_mode() {
  local actual
  actual="$(stat -c '%a' "$1")"
  assert_eq "${actual}" "$2"
}

assert_contains() {
  case "$1" in
    *"$2"*) ;;
    *) fail "expected [$1] to contain [$2]" ;;
  esac
}

run_test() {
  CURRENT_TEST="$1"
  TESTS_RUN=$((TESTS_RUN + 1))
  if ("$1"); then
    printf 'ok %s\n' "$1"
  else
    TESTS_FAILED=$((TESTS_FAILED + 1))
    printf 'not ok %s\n' "$1"
  fi
}

test_load_options() {
  CONFIG_VALUES[workspace]="/share/project"
  CONFIG_VALUES[git_name]="Dev"
  CONFIG_VALUES[git_email]="dev@example.com"
  CONFIG_VALUES[github_token]="token"
  CONFIG_VALUES[opencode_config_json]='{"a":1}'
  CONFIG_VALUES[opencode_auth_json]='{"b":2}'
  CONFIG_VALUES[t3_settings_json]='{"c":3}'
  CONFIG_VALUES[code_server_password]="secret"

  startup_load_options

  assert_eq "${STARTUP_OPTIONS[workspace]}" "/share/project"
  assert_eq "${STARTUP_OPTIONS[git_name]}" "Dev"
  assert_eq "${STARTUP_OPTIONS[git_email]}" "dev@example.com"
  assert_eq "${STARTUP_OPTIONS[github_token]}" "token"
  assert_eq "${STARTUP_OPTIONS[opencode_config_json]}" '{"a":1}'
  assert_eq "${STARTUP_OPTIONS[opencode_auth_json]}" '{"b":2}'
  assert_eq "${STARTUP_OPTIONS[t3_settings_json]}" '{"c":3}'
  assert_eq "${STARTUP_OPTIONS[code_server_password]}" "secret"
}

test_prepare_home() {
  CONFIG_VALUES[workspace]="${TEST_TMP}/workspace"
  CONFIG_VALUES[git_name]="Dev"
  CONFIG_VALUES[git_email]="dev@example.com"
  rm -f "${TEST_TMP}/git.log"

  startup_load_options
  startup_prepare_home

  [ -d "${HOME_DIR}" ] || fail "home not created"
  [ -d "${T3_HOME}" ] || fail "t3 home not created"
  [ -d "${TEST_TMP}/workspace" ] || fail "workspace not created"
  assert_contains "$(cat "${TEST_TMP}/git.log")" "user.name Dev"
  assert_contains "$(cat "${TEST_TMP}/git.log")" "user.email dev@example.com"
  assert_contains "$(cat "${TEST_TMP}/git.log")" "safe.directory ${TEST_TMP}/workspace"
}

test_write_json_valid() {
  local destination="${TEST_TMP}/config/opencode.json"
  _startup_write_json '{"b":2,"a":1}' "${destination}" 600 label message

  assert_file "${destination}"
  assert_mode "${destination}" 600
  assert_eq "$(jq -S -c . "${destination}")" '{"a":1,"b":2}'
}

test_write_json_invalid() {
  local destination="${TEST_TMP}/config/invalid.json"
  _startup_write_json '{invalid' "${destination}" 600 label message

  assert_no_file "${destination}"
}

test_merge_json() {
  local destination="${TEST_TMP}/t3code/userdata/settings.json"
  mkdir -p "$(dirname "${destination}")"
  printf '%s' '{"keep":1,"nested":{"a":1}}' > "${destination}"

  _startup_merge_json '{"nested":{"b":2}}' "${destination}" 600 label message

  assert_file "${destination}"
  assert_mode "${destination}" 600
  assert_eq "$(jq -c . "${destination}")" '{"keep":1,"nested":{"a":1,"b":2}}'
  assert_no_file "${destination}.incoming"
}

test_render_configs() {
  rm -rf "${HOME_DIR}" "${T3_HOME}"
  STARTUP_OPTIONS[opencode_config_json]='{"provider":{"opencode":{"enabled":true}}}'
  STARTUP_OPTIONS[opencode_auth_json]='{"opencode":{"type":"api","key":"secret"}}'
  STARTUP_OPTIONS[t3_settings_json]='{"providers":{"opencode":{"enabled":true}}}'

  startup_render_configs

  assert_file "${HOME_DIR}/.config/opencode/opencode.json"
  assert_mode "${HOME_DIR}/.config/opencode/opencode.json" 644
  assert_file "${HOME_DIR}/.local/share/opencode/auth.json"
  assert_mode "${HOME_DIR}/.local/share/opencode/auth.json" 600
  assert_file "${T3_HOME}/userdata/settings.json"
  assert_mode "${T3_HOME}/userdata/settings.json" 600
}

test_build_extra_env() {
  CONFIG_VALUES[github_token]="token"
  CONFIG_VALUES[env_vars]='[{"name":"ANTHROPIC_API_KEY","value":"sk-ant"},{"name":"bad-name","value":"nope"}]'

  startup_load_options
  startup_build_extra_env

  local joined
  joined="$(printf '%s\n' "${STARTUP_EXTRA_ENV[@]}")"
  assert_contains "${joined}" "GH_TOKEN=token"
  assert_contains "${joined}" "ANTHROPIC_API_KEY=sk-ant"
  case "${joined}" in
    *"bad-name"*) fail "invalid env name was accepted" ;;
  esac
}

test_run_as_dev() {
  local output
  output="$(startup_run_as_dev sh -c 'printf "%s" "$HOME"')"
  assert_eq "${output}" "${HOME_DIR}"
}

test_authenticate_gh() {
  CONFIG_VALUES[github_token]="token"
  rm -f "${TEST_TMP}/gh.log"

  startup_load_options
  startup_authenticate_gh

  assert_contains "$(cat "${TEST_TMP}/gh.log")" "auth login --with-token"
  assert_contains "$(cat "${TEST_TMP}/gh.log")" "auth setup-git"
}

run_test test_load_options
run_test test_prepare_home
run_test test_write_json_valid
run_test test_write_json_invalid
run_test test_merge_json
run_test test_render_configs
run_test test_build_extra_env
run_test test_run_as_dev
run_test test_authenticate_gh

if [ "${TESTS_FAILED}" -ne 0 ]; then
  printf '%d test(s) failed\n' "${TESTS_FAILED}" >&2
  exit 1
fi

printf '%d tests passed\n' "${TESTS_RUN}"
