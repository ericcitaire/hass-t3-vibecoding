#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "${ROOT}/t3_vibecoding/lib/startup.sh"
# shellcheck source=/dev/null
source "${ROOT}/t3_vibecoding/lib/code-server.sh"

TEST_TMP="$(mktemp -d)"
trap 'rm -rf "${TEST_TMP}"' EXIT
HOME_DIR="${TEST_TMP}/home"
T3_HOME="${TEST_TMP}/t3code"

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
  assert_eq "$(stat -c '%a' "$1")" "$2"
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

if [ "${TESTS_FAILED}" -ne 0 ]; then
  printf '%d test(s) failed\n' "${TESTS_FAILED}" >&2
  exit 1
fi

printf '%d tests passed\n' "${TESTS_RUN}"
