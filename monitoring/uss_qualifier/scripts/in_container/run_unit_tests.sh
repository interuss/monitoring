#!/usr/bin/env bash

# This script is intended to be called from within a Docker container running
# mock_uss via the interuss/monitoring image.  In that context, this script is
# the entrypoint into the test definition validation tool.

# Ensure uss_qualifier is the working directory
OS=$(uname)
if [[ $OS == "Darwin" ]]; then
	# OSX uses BSD readlink
	BASEDIR="$(dirname "$0")"
else
	BASEDIR=$(readlink -e "$(dirname "$0")")
fi
cd "${BASEDIR}/../.." || exit 1

TEST_FILES=$(find . -name "*_test.py")

# TEST_FILES must be expanded as separated filenames.
# Therefore SC2086 must be disabled
# shellcheck disable=SC2086
pytest -v $TEST_FILES
