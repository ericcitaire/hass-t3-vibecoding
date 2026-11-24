#!/usr/bin/env bash
# shellcheck disable=SC2034,SC2154 # test fixtures and globals from sourced helpers
set -euo pipefail

# shellcheck source=/dev/null
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/helpers.sh"
# shellcheck source=/dev/null
source "${ROOT}/t3_vibecoding/lib/startup.sh"
reset_test_paths

test_load_options() {
  CONFIG_VALUES[workspace]="/share/project"
  CONFIG_VALUES[git_name]="Dev"
  CONFIG_VALUES[git_email]="dev@example.com"
  CONFIG_VALUES[github_token]="token"
  CONFIG_VALUES[opencode_config_json]='{"a":1}'
  CONFIG_VALUES[opencode_auth_json]='{"b":2}'
  CONFIG_VALUES[t3_settings_json]='{"c":3}'

  startup_load_options

  assert_eq "${STARTUP_OPTIONS[workspace]}" "/share/project"
  assert_eq "${STARTUP_OPTIONS[git_name]}" "Dev"
  assert_eq "${STARTUP_OPTIONS[git_email]}" "dev@example.com"
  assert_eq "${STARTUP_OPTIONS[github_token]}" "token"
  assert_eq "${STARTUP_OPTIONS[opencode_config_json]}" '{"a":1}'
  assert_eq "${STARTUP_OPTIONS[opencode_auth_json]}" '{"b":2}'
  assert_eq "${STARTUP_OPTIONS[t3_settings_json]}" '{"c":3}'
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

test_run_as_dev() {
  local output
  # shellcheck disable=SC2016 # $HOME must expand inside the child shell
  output="$(startup_run_as_dev sh -c 'printf "%s" "$HOME"')"
  assert_eq "${output}" "${HOME_DIR}"

  # T3 picks the integrated terminal's shell from $SHELL.
  # shellcheck disable=SC2016 # $SHELL must expand inside the child shell
  output="$(startup_run_as_dev sh -c 'printf "%s" "$SHELL"')"
  assert_eq "${output}" "/bin/bash"
}

test_log_versions_from_build_stamp() {
  printf '%s' '{"opencode":"1.2.3","t3":"4.5.6","claude":"7.8.9","codex":"0.4.5","copilot":"6.7.8","addon":"0.9.0"}' > "${VERSIONS_FILE}"
  rm -f "${TEST_TMP}/log.info"

  startup_log_versions

  local log
  log="$(cat "${TEST_TMP}/log.info")"
  assert_contains "${log}" "opencode 1.2.3"
  assert_contains "${log}" "t3 4.5.6"
  assert_contains "${log}" "claude 7.8.9"
  assert_contains "${log}" "codex 0.4.5"
  assert_contains "${log}" "copilot 6.7.8"
}

run_test test_load_options
run_test test_prepare_home
run_test test_run_as_dev
run_test test_log_versions_from_build_stamp

finish_tests
