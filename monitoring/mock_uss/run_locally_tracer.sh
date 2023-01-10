#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
"${SCRIPT_DIR}/run_locally_base.sh"

cd "${SCRIPT_DIR}" || exit 1
mkdir -p tracer/logs
# Prevent logs from building up too much by default
rm tracer/logs/*.yaml

AREA='--area=46.974,7.473,46.976,7.479'
LOGS='--output-folder=/logs'
MONITOR='--monitor-rid --monitor-scd'
POLL='--rid-isa-poll-interval=15 --scd-operation-poll-interval=15 --scd-constraint-poll-interval=15'

TRACER_OPTIONS="$AREA $LOGS $MONITOR $POLL"


AUTH="DummyOAuth(http://host.docker.internal:8085/token,tracer)"
DSS="http://host.docker.internal:8082"
PUBLIC_KEY="/var/test-certs/auth2.pem"
AUD=${MOCK_USS_TOKEN_AUDIENCE:-localhost,host.docker.internal}

PORT=8078
BASE_URL="http://${MOCK_USS_TOKEN_AUDIENCE:-host.docker.internal}:${PORT}"

if [ "$CI" == "true" ]; then
  docker_args="--add-host host.docker.internal:host-gateway" # Required to reach other containers in Ubuntu (used for Github Actions)
else
  docker_args=""
fi

# shellcheck disable=SC2086
docker run ${docker_args} --name mock_uss_tracer \
  --rm \
  -e MOCK_USS_AUTH_SPEC="${AUTH}" \
  -e MOCK_USS_DSS_URL="${DSS}" \
  -e MOCK_USS_PUBLIC_KEY="${PUBLIC_KEY}" \
  -e MOCK_USS_TOKEN_AUDIENCE="${AUD}" \
  -e MOCK_USS_BASE_URL="${BASE_URL}" \
  -e MOCK_USS_TRACER_OPTIONS="${TRACER_OPTIONS}" \
  -e MOCK_USS_SERVICES="tracer" \
  -p ${PORT}:5000 \
  -v "${SCRIPT_DIR}/../../build/test-certs:/var/test-certs:ro" \
  -v "${SCRIPT_DIR}/tracer/logs:/logs" \
  "$@" \
  interuss/monitoring \
  mock_uss/start.sh
