#!/usr/bin/with-contenv bashio
set -e

# shellcheck source=/dev/null
source /usr/local/lib/t3-vibecoding/startup.sh
# shellcheck source=/dev/null
source /usr/local/lib/t3-vibecoding/credentials.sh

startup_load_options
startup_prepare_home
startup_prepare_shell
credentials_env
startup_log_versions
credentials_apply

startup_exec_t3
