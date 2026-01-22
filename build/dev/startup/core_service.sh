#!/bin/sh

set -e

# This startup script is meant to be invoked from within a Docker container
# started by docker-compose.yaml, not on a local system.

DEBUG_ON=${1:-0}

# POSIX compliant test to check if with-yugabyte profile is enabled.
if [ "${COMPOSE_PROFILES#*"with-yugabyte"}" != "${COMPOSE_PROFILES}" ]; then
  echo "Using Yugabyte"
  DATASTORE_CONNECTION="-datastore_host ybdb -datastore_user yugabyte --datastore_port 5433"
else
  echo "Using CockroachDB"
  DATASTORE_CONNECTION="-datastore_host crdb.uss1.localutm"
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
  -accepted_jwt_audiences localhost,host.docker.internal,dss.uss1.localutm,dss.uss2.localutm \
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
  -accepted_jwt_audiences localhost,host.docker.internal,dss.uss1.localutm,dss.uss2.localutm \
  -enable_scd \
  -allow_http_base_urls \
  -locality local_dev \
  -public_endpoint http://127.0.0.1:80
fi
