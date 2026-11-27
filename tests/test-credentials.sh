#!/usr/bin/env bash
# shellcheck disable=SC2034,SC2154 # test fixtures and globals from sourced helpers
set -euo pipefail

# shellcheck source=/dev/null
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/helpers.sh"
# shellcheck source=/dev/null
source "${ROOT}/t3_vibecoding/lib/startup.sh"
# shellcheck source=/dev/null
source "${ROOT}/t3_vibecoding/lib/credentials.sh"
reset_test_paths

test_write_json_valid() {
  local destination="${TEST_TMP}/config/opencode.json"
  _credentials_write_json '{"b":2,"a":1}' "${destination}" 600 label message

  assert_file "${destination}"
  assert_mode "${destination}" 600
  assert_eq "$(jq -S -c . "${destination}")" '{"a":1,"b":2}'
}

test_write_json_invalid() {
  local destination="${TEST_TMP}/config/invalid.json"

  if _credentials_write_json '{invalid' "${destination}" 600 label message; then
    fail "invalid JSON was accepted"
  fi

  assert_no_file "${destination}"
}

test_merge_json() {
  local destination="${TEST_TMP}/t3code/userdata/settings.json"
  mkdir -p "$(dirname "${destination}")"
  printf '%s' '{"keep":1,"nested":{"a":1}}' > "${destination}"

  _credentials_merge_json '{"nested":{"b":2}}' "${destination}" 600 label message

  assert_file "${destination}"
  assert_mode "${destination}" 600
  assert_eq "$(jq -S -c . "${destination}")" '{"keep":1,"nested":{"a":1,"b":2}}'
  assert_no_file "${destination}.incoming"
}

test_merge_defaults() {
  local destination="${TEST_TMP}/t3code/defaults/settings.json"

  _credentials_merge_defaults '{"keepAwakeWhileAgentsWork":false,"fresh":1}' "${destination}" 600 label message

  assert_file "${destination}"
  assert_mode "${destination}" 600
  assert_eq "$(jq -S -c . "${destination}")" '{"fresh":1,"keepAwakeWhileAgentsWork":false}'

  printf '%s' '{"keepAwakeWhileAgentsWork":true,"keep":1}' > "${destination}"
  _credentials_merge_defaults '{"keepAwakeWhileAgentsWork":false,"fresh":1}' "${destination}" 600 label message

  assert_eq "$(jq -S -c . "${destination}")" '{"fresh":1,"keep":1,"keepAwakeWhileAgentsWork":true}'
}

test_build_env() {
  CONFIG_VALUES[github_token]="token"
  CONFIG_VALUES[env_vars]='[{"name":"ANTHROPIC_API_KEY","value":"sk-ant"},{"name":"bad-name","value":"nope"}]'

  startup_load_options
  credentials_env

  local joined
  joined="$(printf '%s\n' "${STARTUP_EXTRA_ENV[@]}")"
  assert_contains "${joined}" "GH_TOKEN=token"
  assert_contains "${joined}" "ANTHROPIC_API_KEY=sk-ant"
  case "${joined}" in
    *"bad-name"*) fail "invalid env name was accepted" ;;
  esac
}

test_apply_writes_everything() {
  rm -rf "${HOME_DIR}" "${T3_HOME}"
  rm -f "${TEST_TMP}/gh.log" "${TEST_TMP}/log.info"
  CONFIG_VALUES[github_token]="token"
  CONFIG_VALUES[opencode_config_json]='{"provider":{"opencode":{"enabled":true}}}'
  CONFIG_VALUES[opencode_auth_json]='{"opencode":{"type":"api","key":"secret"}}'
  CONFIG_VALUES[t3_settings_json]='{"providers":{"opencode":{"enabled":true}}}'

  startup_load_options
  credentials_env
  credentials_apply

  assert_file "${HOME_DIR}/.config/opencode/opencode.json"
  assert_mode "${HOME_DIR}/.config/opencode/opencode.json" 644
  assert_file "${HOME_DIR}/.local/share/opencode/auth.json"
  assert_mode "${HOME_DIR}/.local/share/opencode/auth.json" 600
  assert_file "${T3_HOME}/userdata/settings.json"
  assert_mode "${T3_HOME}/userdata/settings.json" 600
  assert_eq "$(jq -S -c . "${T3_HOME}/userdata/settings.json")" \
    '{"keepAwakeWhileAgentsWork":false,"providers":{"opencode":{"enabled":true}}}'

  assert_contains "$(cat "${TEST_TMP}/gh.log")" "auth login --with-token"
  assert_contains "$(cat "${TEST_TMP}/gh.log")" "auth setup-git"

  local summary
  summary="$(cat "${TEST_TMP}/log.info")"
  assert_contains "${summary}" "Applied credentials/config"
  assert_contains "${summary}" "github"
  assert_contains "${summary}" "opencode-config"
  assert_contains "${summary}" "opencode-auth"
  assert_contains "${summary}" "t3-defaults"
  assert_contains "${summary}" "t3-settings"
}

test_user_option_overrides_defaults() {
  rm -rf "${T3_HOME}"
  CONFIG_VALUES[t3_settings_json]='{"keepAwakeWhileAgentsWork":true}'

  startup_load_options
  credentials_apply

  assert_eq "$(jq -S -c . "${T3_HOME}/userdata/settings.json")" '{"keepAwakeWhileAgentsWork":true}'
}

run_test test_write_json_valid
run_test test_write_json_invalid
run_test test_merge_json
run_test test_merge_defaults
run_test test_build_env
run_test test_apply_writes_everything
run_test test_user_option_overrides_defaults

finish_tests
