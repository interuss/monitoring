#!/usr/bin/env bash

set -eo pipefail

# This script will deploy a collection of mock USS servers with docker compose.

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

UID_GID="$(id -u):$(id -g)"
export UID_GID
echo "DC_COMMAND is ${DC_COMMAND}"

declare -a log_folders=( \
    "output/tracer" \
    "output/scdsc_a_interaction_logs" \
    "output/scdsc_interaction_logs" \
  )
for log_folder in "${log_folders[@]}"; do
  mkdir -p "$log_folder"
  if [[ "$DC_COMMAND" == up* ]]; then
    echo "Cleaning up past logs in $log_folder"
    # Prevent logs from building up too much by default
    find "$log_folder" -name "*.yaml" -exec rm {} \;
    find "$log_folder" -name "*.json" -exec rm {} \;
  fi
done

# shellcheck disable=SC2086
docker compose -f docker-compose.yaml -p mocks $DC_COMMAND $DC_OPTIONS
