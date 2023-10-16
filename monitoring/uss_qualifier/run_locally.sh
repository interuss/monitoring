#!/usr/bin/env bash

set -eo pipefail

# Find and change to repo root directory
OS=$(uname)
if [[ "$OS" == "Darwin" ]]; then
	# OSX uses BSD readlink
	BASEDIR="$(dirname "$0")"
else
	BASEDIR=$(readlink -e "$(dirname "$0")")
fi
cd "${BASEDIR}/../.." || exit 1

if [ -z "$DO_NOT_BUILD_MONITORING" ]; then
  monitoring/build.sh || exit 1
  export DO_NOT_BUILD_MONITORING=true
fi

CONFIG_NAME="${1:-ALL}"

# https://stackoverflow.com/a/9057392
# shellcheck disable=SC2124
OTHER_ARGS=${@:2}

if [ "$CONFIG_NAME" == "ALL" ]; then
  declare -a all_configurations=( \
    "configurations.dev.noop" \
    "configurations.dev.dss_probing" \
    "configurations.dev.geoawareness_cis" \
    "configurations.dev.generate_rid_test_data" \
    "configurations.dev.geospatial_comprehension" \
    "configurations.dev.general_flight_auth" \
    "configurations.dev.f3548" \
    "configurations.dev.f3548_self_contained" \
    "configurations.dev.netrid_v22a" \
    "configurations.dev.uspace" \
  )
  # TODO: Add configurations.dev.netrid_v19
  echo "Running configurations: ${all_configurations[*]}"
  for configuration_name in "${all_configurations[@]}"; do
    monitoring/uss_qualifier/run_locally.sh "$configuration_name"
  done
else
  CONFIG_FLAG="--config ${CONFIG_NAME}"

  AUTH_SPEC='DummyOAuth(http://oauth.authority.localutm:8085/token,uss_qualifier)'

  QUALIFIER_OPTIONS="$CONFIG_FLAG $OTHER_ARGS"

  OUTPUT_DIR="monitoring/uss_qualifier/output"
  mkdir -p "$OUTPUT_DIR"

  CACHE_DIR="monitoring/uss_qualifier/.templates_cache"
  mkdir -p "$CACHE_DIR"

  if [ "$CI" == "true" ]; then
    docker_args="--add-host host.docker.internal:host-gateway" # Required to reach other containers in Ubuntu (used for Github Actions)
  else
    docker_args="-it"
  fi

  start_time=$(date +%Y-%m-%dT%H:%M:%S)
  echo "========== Running uss_qualifier for configuration ${CONFIG_NAME} =========="
  # shellcheck disable=SC2086
  docker run ${docker_args} --name uss_qualifier \
    --rm \
    --network interop_ecosystem_network \
    -u "$(id -u):$(id -g)" \
    -e PYTHONBUFFERED=1 \
    -e AUTH_SPEC=${AUTH_SPEC} \
    -e USS_QUALIFIER_STOP_FAST=${USS_QUALIFIER_STOP_FAST:-} \
    -e MONITORING_GITHUB_ROOT=${MONITORING_GITHUB_ROOT:-} \
    -v "$(pwd)/$OUTPUT_DIR:/app/$OUTPUT_DIR" \
    -v "$(pwd)/$CACHE_DIR:/app/$CACHE_DIR" \
    -w /app/monitoring/uss_qualifier \
    interuss/monitoring \
    python main.py $QUALIFIER_OPTIONS
  echo "========== Completed uss_qualifier for configuration ${CONFIG_NAME} =========="
fi

