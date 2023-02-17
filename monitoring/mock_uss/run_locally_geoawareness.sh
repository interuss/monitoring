#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
if [ -z "${DO_NOT_BUILD_MONITORING}" ]; then
  "${SCRIPT_DIR}/../build.sh" || exit 1
fi

PUBLIC_KEY="/var/test-certs/auth2.pem"
AUD=${MOCK_USS_TOKEN_AUDIENCE:-localhost,host.docker.internal}
container_name="mock_uss_geoawareness"

PORT=8076

if [ "$CI" == "true" ]; then
  docker_args="--add-host host.docker.internal:host-gateway" # Required to reach other containers in Ubuntu (used for Github Actions)
else
  docker_args="-it"
fi

docker_command="mock_uss/start.sh"
if [ "$TEST" == "true" ]; then
  AUD="localhost"
  docker_command="mock_uss/test.sh"
fi

docker container rm -f ${container_name} || echo "${container_name} container was not already running"

# shellcheck disable=SC2086
docker run ${docker_args} --name ${container_name} \
  -e MOCK_USS_PUBLIC_KEY="${PUBLIC_KEY}" \
  -e MOCK_USS_TOKEN_AUDIENCE="${AUD}" \
  -e MOCK_USS_SERVICES="geoawareness" \
  -p ${PORT}:5000 \
  -v "${SCRIPT_DIR}/../../build/test-certs:/var/test-certs:ro" \
  "$@" \
  interuss/monitoring \
  ${docker_command}
