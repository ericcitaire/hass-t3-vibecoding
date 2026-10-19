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

startup_exec_t3
