#!/usr/bin/env bash

set -eo pipefail

# This script will deploy an interoperability ecosystem consisting of a chosen number of DSS instances and a dummy OAuth
# server (all accessible on the interop_ecosystem_network) with docker compose using the DSS image from Docker Hub.
# Run `./run_locally.sh up -d` to start a single DSS instance using CockroachDB.
# The following environment variables may be used:
# NUM_USS: number of USSs
# NUM_NODES: number of nodes per USS
# DB_TYPE: crdb or ybdb

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

NUM_USS=${NUM_USS:-2}
NUM_NODES=${NUM_NODES:-1}
DB_TYPE=${DB_TYPE:-crdb}

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

if [[ "$DC_COMMAND" == up* ]]; then
  echo "Creating networks..."
  docker network create --subnet=172.27.0.0/16 \
                        --ip-range=172.27.0.0/24 \
                        --gateway=172.27.0.1 \
                        dss_internal_network || true
  docker network create interop_ecosystem_network || true
  echo "Starting containers..."
fi

for ((i=1; i<=NUM_USS; i++)); do
  for ((j=1; j<=NUM_NODES; j++)); do
    export USS_IDX=$i
    export USS_NODE_IDX=$j
    PADDED_NODE_IDX=$(printf "%02d" $(( (i-1) * NUM_NODES + j)))
    export PADDED_NODE_IDX

    export COMPOSE_PROFILES=${DB_TYPE}
    if [ "$i" -eq 1 ] && [ "$j" -eq 1 ]; then
      export COMPOSE_PROFILES=${COMPOSE_PROFILES},oauth
    fi
    if [ "$i" -eq "$NUM_USS" ] && [ "$j" -eq "$NUM_NODES" ]; then
      export COMPOSE_PROFILES=${COMPOSE_PROFILES},bootstrap-${DB_TYPE}
    fi

    # shellcheck disable=SC2086
    docker compose -f docker-compose.yaml -p "local_infra_${USS_IDX}-${USS_NODE_IDX}" $DC_COMMAND $DC_OPTIONS &
  done
done
wait

if [[ "$DC_COMMAND" == "down" ]]; then
  echo "Removing networks..."
  docker network rm dss_internal_network || true
  docker network rm interop_ecosystem_network || true
fi
