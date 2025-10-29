#!/bin/sh

set -e

# This startup script is meant to be invoked from within a Docker container
# started by docker-compose.yaml, not on a local system.

DEBUG_ON=${1:-0}

if [ "$DEBUG_ON" = "1" ]; then
  echo "Debug Mode: on"

  dlv --headless --listen=:4000 --api-version=2 --accept-multiclient exec --continue /usr/bin/core-service -- \
  -cockroach_host crdb.uss1.localutm \
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

  /usr/bin/core-service \
  -cockroach_host crdb.uss1.localutm \
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
