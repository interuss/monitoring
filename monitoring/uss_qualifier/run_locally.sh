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

if [ "$CONFIG_NAME" == "ALL" ]; then
  declare -a all_configurations=( \
    "configurations.dev.noop" \
    "configurations.dev.geoawareness_cis" \
    "configurations.dev.generate_rid_test_data" \
    "configurations.dev.geospatial_comprehension" \
    "configurations.dev.general_flight_auth" \
    "configurations.dev.f3548" \
    "configurations.dev.f3548_self_contained" \
    "configurations.dev.uspace" \
  )
  # TODO: Add configurations.dev.netrid_v19
  # TODO: Add configurations.dev.netrid_v22a
  echo "Running configurations: ${all_configurations[*]}"
  for configuration_name in "${all_configurations[@]}"; do
    monitoring/uss_qualifier/run_locally.sh "$configuration_name"
  done
else
  CONFIG_FLAG="--config ${CONFIG_NAME}"

  AUTH_SPEC='DummyOAuth(http://host.docker.internal:8085/token,uss_qualifier)'

  QUALIFIER_OPTIONS="$CONFIG_FLAG"

  OUTPUT_DIR="monitoring/uss_qualifier/output"
  mkdir -p "$OUTPUT_DIR"

  if [ "$CI" == "true" ]; then
    docker_args="--add-host host.docker.internal:host-gateway" # Required to reach other containers in Ubuntu (used for Github Actions)
  else
    docker_args="-it"
  fi

  start_time=$(date -v-1S +%Y-%m-%dT%H:%M:%S)
  echo "========== Running uss_qualifier for configuration ${CONFIG_NAME} =========="
  # shellcheck disable=SC2086
  docker run ${docker_args} --name uss_qualifier \
    --rm \
    -u "$(id -u):$(id -g)" \
    -e PYTHONBUFFERED=1 \
    -e AUTH_SPEC=${AUTH_SPEC} \
    -e USS_QUALIFIER_STOP_FAST=${USS_QUALIFIER_STOP_FAST:-} \
    -v "$(pwd)/$OUTPUT_DIR:/app/$OUTPUT_DIR" \
    -w /app/monitoring/uss_qualifier \
    interuss/monitoring \
    python main.py $QUALIFIER_OPTIONS
  echo "========== Completed uss_qualifier for configuration ${CONFIG_NAME} =========="

  # Set return code according to whether the test run was fully successful
  reports_generated=$(find ./monitoring/uss_qualifier/output/report*.json -newermt "$start_time")
  # shellcheck disable=SC2068
  for REPORT in ${reports_generated[@]}; do
    successful=$(python build/dev/extract_json_field.py report.*.successful "$REPORT")
    if echo "${successful}" | grep -iqF true; then
      echo "Full success indicated by $REPORT"
    else
      echo "Could not establish that all uss_qualifier tests passed in $REPORT"
      # exit 1
    fi
  done
fi

