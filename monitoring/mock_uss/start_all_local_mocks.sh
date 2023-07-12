#!/bin/bash

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

RID_VERSION=${RID_VERSION:-"F3411-22a"}
RID_EXT=""
if [ "$RID_VERSION" = "F3411-19" ]; then
	RID_EXT="_v19"
fi

monitoring/mock_uss/run_locally_scdsc.sh -d
export DO_NOT_BUILD_MONITORING=true
monitoring/mock_uss/run_locally_ridsp${RID_EXT}.sh -d
monitoring/mock_uss/run_locally_riddp${RID_EXT}.sh -d
monitoring/mock_uss/run_locally_geoawareness.sh -d
monitoring/mock_uss/run_locally_atproxy_client.sh -d
monitoring/mock_uss/run_locally_tracer${RID_EXT}.sh -d
monitoring/mock_uss/wait_for_mock_uss.sh mock_uss_scdsc
monitoring/mock_uss/wait_for_mock_uss.sh mock_uss_ridsp${RID_EXT}
monitoring/mock_uss/wait_for_mock_uss.sh mock_uss_riddp${RID_EXT}
monitoring/mock_uss/wait_for_mock_uss.sh mock_uss_geoawareness
monitoring/mock_uss/wait_for_mock_uss.sh mock_uss_tracer${RID_EXT}
