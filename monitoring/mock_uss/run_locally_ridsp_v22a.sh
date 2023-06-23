#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
if [ -z "${DO_NOT_BUILD_MONITORING}" ]; then
  "${SCRIPT_DIR}/../build.sh" || exit 1
fi

MOCK_CONTAINER_NAME="mock_uss_ridsp_v22a" \
MOCK_USS_RID_VERSION="F3411-22a" \
PORT=8081 \
"${SCRIPT_DIR}/run_locally_ridsp.sh" "$@"