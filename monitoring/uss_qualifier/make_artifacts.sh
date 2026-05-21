#!/usr/bin/env bash

set -eo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <REPORT_PATH> [<CONFIG_NAME(s)> [<OUTPUT_PATH>]]"
  echo "Generates artifacts according to the specified configuration(s) using the specified report(s)"
  echo "  <REPORT_PATH>: Location (on the host machine) of the report file.  Relative paths are RELATIVE TO THE REPO ROOT."
  echo "  <CONFIG_NAME>: Location of the configuration file describing what artifacts to make.  Must be built into the monitoring image (in configurations/personal, for instance).  If not specified, use artifacts configuration from report."
  echo "  <OUTPUT_PATH>: Location (on the host machine) to which artifacts should be written.  Defaults to folder containing the report."
  echo "Examples:"
  echo "  ./monitoring/uss_qualifier/make_artifacts.sh ~/Downloads/be0bbe7c-4670-43f5-906a-594be69087f4/report.json configurations.dev.f3548_self_contained"
  echo "  ./make_artifacts.sh monitoring/uss_qualifier/output/f3548_self_contained/report.json configurations.personal.custom_artifacts"
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

REPORT_LOCATION="${1}"

# TODO: Retrieve local copy of report if location starts with "http"

REPORT_PATH=$(realpath "${REPORT_LOCATION}")
echo "Reading report from (host machine): ${REPORT_PATH}"
REPORT_FILENAME=$(basename "${REPORT_PATH}")
MAKE_ARTIFACTS_OPTIONS="--report file:///input/${REPORT_FILENAME}"

if [ "$#" -gt 1 ]; then
  CONFIG_NAME="${2}"
  echo "Generating artifacts from configuration (in image): ${CONFIG_NAME}"
  MAKE_ARTIFACTS_OPTIONS="$MAKE_ARTIFACTS_OPTIONS --config $CONFIG_NAME"
fi

if [ "$#" -gt 2 ]; then
  OUTPUT_PATH=$(realpath "${3}")
else
  OUTPUT_PATH=$(dirname "${REPORT_PATH}")
fi
OUTPUT_FOLDERNAME=$(basename "${OUTPUT_PATH}")
echo "Writing artifacts to (host machine): ${OUTPUT_PATH}"
MAKE_ARTIFACTS_OPTIONS="$MAKE_ARTIFACTS_OPTIONS --output-path output/${OUTPUT_FOLDERNAME}"

mkdir -p "$OUTPUT_PATH"

CACHE_DIR="monitoring/uss_qualifier/.templates_cache"
mkdir -p "$CACHE_DIR"

# shellcheck disable=SC2086
docker run --name uss_qualifier \
  --rm \
  -u "$(id -u):$(id -g)" \
  -e PYTHONBUFFERED=1 \
  -e MONITORING_GITHUB_ROOT=${MONITORING_GITHUB_ROOT:-} \
  -v "${REPORT_PATH}:/input/${REPORT_FILENAME}" \
  -v "${OUTPUT_PATH}:/app/monitoring/uss_qualifier/output/${OUTPUT_FOLDERNAME}" \
  -v "$(pwd)/$CACHE_DIR:/app/$CACHE_DIR" \
  -w /app/monitoring/uss_qualifier \
  interuss/monitoring \
  uv run make_artifacts.py $MAKE_ARTIFACTS_OPTIONS
