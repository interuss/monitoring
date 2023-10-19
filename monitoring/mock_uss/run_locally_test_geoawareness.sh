#!/usr/bin/env bash

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

PUBLIC_KEY="/var/test-certs/auth2.pem"
container_name="mock_uss_geoawareness_test"
AUD="localhost"
docker_command="mock_uss/test.sh"

PORT=8076

if [ "$CI" == "true" ]; then
  docker_args="--add-host host.docker.internal:host-gateway" # Required to reach other containers in Ubuntu (used for Github Actions)
else
  docker_args="-it"
fi

docker container rm -f ${container_name} || echo "${container_name} container was not already running"

# shellcheck disable=SC2086
docker run ${docker_args} --rm --name ${container_name} \
  -e MOCK_USS_PUBLIC_KEY="${PUBLIC_KEY}" \
  -e MOCK_USS_TOKEN_AUDIENCE="${AUD}" \
  -e MOCK_USS_SERVICES="geoawareness" \
  -p ${PORT}:5000 \
  -v "$(pwd)/build/test-certs:/var/test-certs:ro" \
  "$@" \
  interuss/monitoring \
  ${docker_command}
