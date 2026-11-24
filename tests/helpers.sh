#!/usr/bin/env bash
# Shared setup and assertions for the add-on shell module tests.
# shellcheck disable=SC2034 # shared globals consumed by the sourced test files

HELPERS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HELPERS_DIR}/.." && pwd)"

TEST_TMP="$(mktemp -d)"
trap 'rm -rf "${TEST_TMP}"' EXIT
STUB_DIR="${TEST_TMP}/bin"
mkdir -p "${STUB_DIR}"

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
printf '2.1.2\n'
EOF

cat > "${STUB_DIR}/t3" <<EOF
#!/usr/bin/env bash
printf 't3 %s\n' "\$*" >> "${TEST_TMP}/t3.log"
if [ "\${1:-}" = "--version" ]; then printf '0.1.0\n'; fi
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

bashio::log.info() {
  printf 'INFO: %s\n' "$*" >> "${TEST_TMP}/log.info"
}

bashio::log.warning() {
  printf 'WARN: %s\n' "$*" >&2
}

chown() { :; }

reset_test_paths() {
  HOME_DIR="${TEST_TMP}/home"
  T3_HOME="${TEST_TMP}/t3code"
  VERSIONS_FILE="${TEST_TMP}/versions.json"
  STARTUP_PATH="${STUB_DIR}:/usr/bin:/bin"
}

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

finish_tests() {
  if [ "${TESTS_FAILED}" -ne 0 ]; then
    printf '%d test(s) failed\n' "${TESTS_FAILED}" >&2
    exit 1
  fi

  printf '%d tests passed\n' "${TESTS_RUN}"
}
