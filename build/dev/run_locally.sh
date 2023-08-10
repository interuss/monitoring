#!/usr/bin/env bash

set -eo pipefail

# This script will deploy an interoperability ecosystem consisting of a standalone DSS instance and dummy OAuth server
# (both accessible on the interop_ecosystem_network) with docker compose using the DSS image from Docker Hub.

if [[ -z $(command -v docker) ]]; then
  echo "docker is required but not installed.  Visit https://docs.docker.com/install/ to install."
  exit 1
fi

OS=$(uname)
if [[ "$OS" == "Darwin" ]]; then
	# OSX uses BSD readlink
	BASEDIR="$(dirname "$0")"
else
	BASEDIR=$(readlink -e "$(dirname "$0")")
fi

cd "${BASEDIR}" || exit 1

DC_COMMAND=$*

if [[ ! "$DC_COMMAND" ]]; then
  DC_COMMAND="up"
  DC_OPTIONS="--build"
elif [[ "$DC_COMMAND" == "down" ]]; then
  DC_OPTIONS="--volumes --remove-orphans"
elif [[ "$DC_COMMAND" == "debug" ]]; then
  DC_COMMAND=up
  export DEBUG_ON=1
fi

# shellcheck disable=SC2086
docker compose -f docker-compose.yaml -p local_infra $DC_COMMAND $DC_OPTIONS
