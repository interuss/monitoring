#!/usr/bin/env bash

set -eo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <CONFIG_NAME(s)> <REPORT_NAME(s)>"
  echo "Generates artifacts according to the specified configuration(s) using the specified report(s)"
  echo "<CONFIG_NAME>: Location of the configuration file (or multiple locations separated by commas)."
  echo "<REPORT_NAME>: Location of the report file (or multiple locations separated by commas)."
  exit 1
fi

# Find and change to repo root directory
OS=$(uname)
if [[ "$OS" == "Darwin" ]]; then
	# OSX uses BSD readlink
	BASEDIR="$(dirname "$0")"
else
	BASEDIR=$(readlink -e "$(dirname "$0")")
fi
cd "${BASEDIR}/../.." || exit 1

(
cd monitoring || exit 1
make image
)

CONFIG_NAME="${1}"

REPORT_NAME="${2}"

echo "Generating artifacts from configuration(s): ${CONFIG_NAME}"
echo "Reading report(s) from: ${REPORT_NAME}"

OUTPUT_DIR="monitoring/uss_qualifier/output"
mkdir -p "$OUTPUT_DIR"

CACHE_DIR="monitoring/uss_qualifier/.templates_cache"
mkdir -p "$CACHE_DIR"

# shellcheck disable=SC2086
docker run --name uss_qualifier \
  --rm \
  -u "$(id -u):$(id -g)" \
  -e PYTHONBUFFERED=1 \
  -e MONITORING_GITHUB_ROOT=${MONITORING_GITHUB_ROOT:-} \
  -v "$(pwd)/$OUTPUT_DIR:/app/$OUTPUT_DIR" \
  -v "$(pwd)/$CACHE_DIR:/app/$CACHE_DIR" \
  -w /app/monitoring/uss_qualifier \
  interuss/monitoring \
  python make_artifacts.py --config "$CONFIG_NAME" --report "$REPORT_NAME"
