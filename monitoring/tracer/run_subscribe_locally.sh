#!/usr/bin/env bash

set -eo pipefail

# Find and change to repo root directory
OS=$(uname)
if [[ "$OS" == "Darwin" ]]; then
	# OSX uses BSD readlink
	BASEDIR="$(dirname "$0")"
else
	BASEDIR=$(readlink -e "$(dirname "$0")")
fi
cd "${BASEDIR}/../.." || exit 1

echo '#########################################################################'
echo '## NOTE: Prerequisite to run this command is:                          ##'
echo '## Local DSS instance + Dummy OAuth server (/build/dev/run_locally.sh) ##'
echo '#########################################################################'

monitoring/build.sh || exit 1

AUTH='--auth=DummyOAuth(http://host.docker.internal:8085/token,uss1)'
DSS='--dss=http://host.docker.internal:8082'
AREA='--area=34.1234,-123.4567,34.4567,-123.1234'
LOGS='--output-folder=/logs'
BASE_URL='--base-url=http://host.docker.internal:5000'
KML_SERVER='--kml-server=https://example.com/kmlgeneration'
KML_FOLDER='--kml-folder=test/localmock'
MONITOR='--monitor-rid --monitor-scd'
PORT=5000

TRACER_OPTIONS="$AUTH $DSS $AREA $LOGS $BASE_URL $KML_SERVER $KML_FOLDER $MONITOR"

docker run --name tracer_subscribe \
  --rm \
  -e TRACER_OPTIONS="${TRACER_OPTIONS}" \
  -p ${PORT}:5000 \
  -v "$(pwd)/logs:/logs" \
  --workdir=/app/monitoring/tracer \
  interuss/monitoring \
  gunicorn \
    --preload \
    --workers=2 \
    --bind=0.0.0.0:5000 \
    monitoring.tracer.uss_receiver:webapp
