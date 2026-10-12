#!/usr/bin/env bash

set -eo pipefail

# This script is intended to be called from within a Docker container running
# the interuss/monitoring-dev image.  In that context, this script runs the
# benchmarker unit tests.

# Ensure benchmarker is the working directory
OS=$(uname)
if [[ $OS == "Darwin" ]]; then
	# OSX uses BSD readlink
	BASEDIR="$(dirname "$0")"
else
	BASEDIR=$(readlink -e "$(dirname "$0")")
fi
cd "${BASEDIR}/../.." || exit 1

uv run pytest
