#!/usr/bin/env bash

set -eo pipefail
set -o xtrace

# Find and change to repo root directory
OS=$(uname)
if [[ "$OS" == "Darwin" ]]; then
	# OSX uses BSD readlink
	BASEDIR="$(dirname "$0")"
else
	BASEDIR=$(readlink -e "$(dirname "$0")")
fi
cd "${BASEDIR}/../../.." || exit 1

(
cd monitoring || exit 1
make image
)

# shellcheck disable=SC2086
docker run --name test_documentation_formatter \
  --rm \
  -v "$(pwd):/app" \
  -e MONITORING_GITHUB_ROOT=${MONITORING_GITHUB_ROOT:-} \
  interuss/monitoring \
  uss_qualifier/scripts/in_container/format_test_documentation.sh
