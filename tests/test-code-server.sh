#!/usr/bin/env bash
# shellcheck disable=SC2034,SC2154 # test fixtures and globals from sourced helpers
set -euo pipefail

# shellcheck source=/dev/null
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/helpers.sh"
# shellcheck source=/dev/null
source "${ROOT}/t3_vibecoding/lib/startup.sh"
# shellcheck source=/dev/null
source "${ROOT}/t3_vibecoding/lib/credentials.sh"
# shellcheck source=/dev/null
source "${ROOT}/t3_vibecoding/lib/code-server.sh"
reset_test_paths

test_prepare_requires_password() {
  rm -rf "${HOME_DIR}"

  if code_server_prepare ""; then
    fail "prepare succeeded without a password"
  fi

  assert_no_file "${HOME_DIR}/.config/code-server/config.yaml"
}

test_prepare_writes_config() {
  rm -rf "${HOME_DIR}"
  local config="${HOME_DIR}/.config/code-server/config.yaml"

  code_server_prepare 'p@ss "word" #1'

  assert_file "${config}"
  assert_mode "${config}" 600
  assert_contains "$(cat "${config}")" "bind-addr: 0.0.0.0:${CODE_SERVER_PORT}"
  assert_contains "$(cat "${config}")" "auth: password"
  assert_contains "$(cat "${config}")" 'password: "p@ss \"word\" #1"'
}

run_test test_prepare_requires_password
run_test test_prepare_writes_config

finish_tests
