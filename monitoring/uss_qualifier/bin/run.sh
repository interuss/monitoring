#!/usr/bin/env bash
# This script builds and executes the uss qualifier.

set -eo pipefail

if [[ $# == 0 ]]; then
  echo "Usage: $0 <CONFIG_LOCATION> [AUTH]"
  echo "Builds and executes the uss qualifier"
  echo "<CONFIG_LOCATION>: Location of the configuration file."
  echo "[AUTH]: Location of the configuration file."
  exit 1
fi
# Get absolute path of the config file provided
CONFIG_LOCATION="$(cd "$(dirname "$1")"; pwd)/$(basename "$1")"

# Find and change to repo root directory
OS=$(uname)
if [[ "$OS" == "Darwin" ]]; then
	# OSX uses BSD readlink
	BASEDIR="$(dirname "$0")"
else
	BASEDIR=$(readlink -e "$(dirname "$0")")
fi
cd "${BASEDIR}/../../.." || exit 1

OUTPUT_DIR="monitoring/uss_qualifier/output"
mkdir -p "$OUTPUT_DIR"

AUTH="${2:-NoAuth()}"

QUALIFIER_OPTIONS="--auth $AUTH --config /config.json --report output/report.json"

(
cd monitoring || exit 1
make image
)

if [ "$CI" == "true" ]; then
  docker_args="--add-host host.docker.internal:host-gateway" # Required to reach other containers in Ubuntu (used for Github Actions)
else
  docker_args="-it"
fi

# shellcheck disable=SC2086
docker run ${docker_args} --name uss_qualifier \
  --rm \
  -e QUALIFIER_OPTIONS="${QUALIFIER_OPTIONS}" \
  -e PYTHONBUFFERED=1 \
  -v "$(pwd)/$OUTPUT_DIR:/app/$OUTPUT_DIR" \
  -v "${CONFIG_LOCATION}:/config.json" \
  -w /app/monitoring/uss_qualifier \
  interuss/monitoring \
  python main.py $QUALIFIER_OPTIONS
