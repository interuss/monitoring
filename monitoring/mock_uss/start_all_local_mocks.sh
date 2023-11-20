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

(
cd monitoring || exit 1
make image
)

./monitoring/mock_uss/run_locally.sh up -d

monitoring/mock_uss/wait_for_mock_uss.sh mock_uss_scdsc_a
monitoring/mock_uss/wait_for_mock_uss.sh mock_uss_scdsc_b
monitoring/mock_uss/wait_for_mock_uss.sh mock_uss_geoawareness
monitoring/mock_uss/wait_for_mock_uss.sh mock_uss_ridsp_v19
monitoring/mock_uss/wait_for_mock_uss.sh mock_uss_riddp_v19
monitoring/mock_uss/wait_for_mock_uss.sh mock_uss_ridsp
monitoring/mock_uss/wait_for_mock_uss.sh mock_uss_riddp
monitoring/mock_uss/wait_for_mock_uss.sh mock_uss_tracer
monitoring/mock_uss/wait_for_mock_uss.sh mock_uss_scdsc_interaction_log
