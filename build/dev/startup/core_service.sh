#!/bin/sh
# shellcheck disable=SC2086

set -e

# This startup script is meant to be invoked from within a Docker container
# started by docker-compose.yaml, not on a local system.

DEBUG_ON=${1:-0}
JWT_AUDIENCES="localhost,host.docker.internal,${JWT_AUDIENCES}"

# apply netem config for intra/inter-USS subnets, if requested
if [ -n "$INTRA_USS_NETEM_CONF" ] || [ -n "$INTER_USS_NETEM_CONF" ]; then
  apk add iproute2-tc

  # create handle on default interface
  tc qdisc add dev eth0 root handle 1: prio

  if [ -n "$INTRA_USS_NETEM_CONF" ]; then
    tc qdisc add dev eth0 parent 1:2 handle 30: netem $INTRA_USS_NETEM_CONF
    tc filter add dev eth0 parent 1:0 protocol ip prio 1 u32 match ip dst "$INTRA_USS_SUBNET" flowid 1:2
  fi

  if [ -n "$INTER_USS_NETEM_CONF" ]; then
    tc qdisc add dev eth0 parent 1:3 handle 31: netem $INTER_USS_NETEM_CONF
    tc filter add dev eth0 parent 1:0 protocol ip prio 2 u32 match ip dst "$INTER_USS_SUBNET" flowid 1:3
  fi
fi

# POSIX compliant tests to select the datastore backend.
if [ "${COMPOSE_PROFILES#*"ybdb"}" != "${COMPOSE_PROFILES}" ]; then
  echo "Using Yugabyte"
  DATASTORE_CONNECTION="-datastore_host ${DATASTORE_HOST} -datastore_user yugabyte --datastore_port 5433"
  DB_PORT=5433
elif [ "${COMPOSE_PROFILES#*"raft"}" != "${COMPOSE_PROFILES}" ]; then
  echo "Using raft"
  DATASTORE_CONNECTION="-store_type raft -raft_node_id=${RAFT_ID} -rid_raft_peers=${RID_RAFT_NODES} -scd_raft_peers=${SCD_RAFT_NODES} -aux_raft_peers=${AUX_RAFT_NODES} -raft_datadir /raftdata"
  DB_PORT=
else
  echo "Using CockroachDB"
  DATASTORE_CONNECTION="-datastore_host ${DATASTORE_HOST}"
  DB_PORT=26257
fi

# raft has no external datastore to wait for.
if [ -n "$DB_PORT" ]; then
  echo "Waiting for datastore ${DATASTORE_HOST}:${DB_PORT}..."
  until nc -z -w 2 "${DATASTORE_HOST}" "${DB_PORT}" 2>/dev/null; do
    echo "Datastore ${DATASTORE_HOST}:${DB_PORT} is not available yet, sleeping..."
    sleep 2
  done
  echo "Datastore ${DATASTORE_HOST}:${DB_PORT} is online!"
fi

if [ "$DEBUG_ON" = "1" ]; then
  echo "Debug Mode: on"

  # Linter is disabled to properly unwrap $DATASTORE_CONNECTION.
  # shellcheck disable=SC2086
  dlv --headless --listen=:4000 --api-version=2 --accept-multiclient exec --continue /usr/bin/core-service -- \
  ${DATASTORE_CONNECTION} \
  -public_key_files /var/test-certs/auth2.pem \
  -log_format console \
  -dump_requests \
  -addr :80 \
  -accepted_jwt_audiences ${JWT_AUDIENCES} \
  -enable_scd \
  -allow_http_base_urls \
  -locality local_dev \
  -public_endpoint http://127.0.0.1:80
else
  echo "Debug Mode: off"

  # Linter is disabled to properly unwrap $DATASTORE_CONNECTION.
  # shellcheck disable=SC2086
  /usr/bin/core-service \
  ${DATASTORE_CONNECTION} \
  -public_key_files /var/test-certs/auth2.pem \
  -log_format console \
  -dump_requests \
  -addr :80 \
  -accepted_jwt_audiences ${JWT_AUDIENCES} \
  -enable_scd \
  -allow_http_base_urls \
  -locality local_dev \
  -public_endpoint http://127.0.0.1:80
fi
