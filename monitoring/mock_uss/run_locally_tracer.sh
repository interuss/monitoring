#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
if [ -z "${DO_NOT_BUILD_MONITORING}" ]; then
  "${SCRIPT_DIR}/../build.sh" || exit 1
fi

cd "${SCRIPT_DIR}" || exit 1

OUTPUT_DIR="output/tracer"
mkdir -p "$OUTPUT_DIR"
# Prevent logs from building up too much by default
find "$OUTPUT_DIR" -name "*.yaml" -exec rm {} \;

AREA='--area=46.974,7.473,46.976,7.479'
LOGS="--output-folder=$OUTPUT_DIR"
MONITOR='--monitor-rid --monitor-scd'
POLL='--rid-isa-poll-interval=15 --scd-operation-poll-interval=15 --scd-constraint-poll-interval=15'

TRACER_OPTIONS="$AREA $LOGS $MONITOR $POLL"


PORT=${PORT:-8078}
AUTH="DummyOAuth(http://host.docker.internal:8085/token,tracer)"
DSS=${MOCK_USS_DSS_URL:-"http://host.docker.internal:8082"}
PUBLIC_KEY="/var/test-certs/auth2.pem"
AUD=${MOCK_USS_TOKEN_AUDIENCE:-localhost,host.docker.internal}

RID_VERSION=${MOCK_USS_RID_VERSION:-"F3411-22a"}
CONTAINER_NAME=${MOCK_CONTAINER_NAME:-"mock_uss_tracer"}

BASE_URL="http://${MOCK_USS_TOKEN_AUDIENCE:-host.docker.internal}:${PORT}"

if [ "$CI" == "true" ]; then
  docker_args="--add-host host.docker.internal:host-gateway" # Required to reach other containers in Ubuntu (used for Github Actions)
else
  docker_args="-it"
fi

docker container rm -f "${CONTAINER_NAME}" || echo "No pre-existing ${CONTAINER_NAME} container to remove"

# shellcheck disable=SC2086
docker run ${docker_args} --name "${CONTAINER_NAME}" \
  -u "$(id -u):$(id -g)" \
  -e MOCK_USS_AUTH_SPEC="${AUTH}" \
  -e MOCK_USS_DSS_URL="${DSS}" \
  -e MOCK_USS_PUBLIC_KEY="${PUBLIC_KEY}" \
  -e MOCK_USS_TOKEN_AUDIENCE="${AUD}" \
  -e MOCK_USS_BASE_URL="${BASE_URL}" \
  -e MOCK_USS_TRACER_OPTIONS="${TRACER_OPTIONS}" \
  -e MOCK_USS_SERVICES="tracer" \
  -e MOCK_USS_RID_VERSION="${RID_VERSION}" \
  -p ${PORT}:5000 \
  -v "${SCRIPT_DIR}/../../build/test-certs:/var/test-certs:ro" \
  -v "$(pwd)/$OUTPUT_DIR:/app/monitoring/mock_uss/$OUTPUT_DIR" \
  -w /app/monitoring/mock_uss \
  "$@" \
  interuss/monitoring \
  ./start.sh
