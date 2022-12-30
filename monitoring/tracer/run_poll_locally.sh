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
KML_SERVER='--kml-server=https://example.com/kmlgeneration'
KML_FOLDER='--kml-folder=test/localmock'
MONITOR='--rid-isa-poll-interval=15 --scd-operation-poll-interval=15 --scd-constraint-poll-interval=15'

TRACER_OPTIONS="$AUTH $DSS $AREA $LOGS $KML_SERVER $KML_FOLDER $MONITOR"

# shellcheck disable=SC2086
docker run --name tracer_poll \
  --rm \
  -e TRACER_OPTIONS="$TRACER_OPTIONS" \
  -v "$(pwd)/logs:/logs" \
  --workdir=/app/monitoring/tracer \
  interuss/monitoring \
  python tracer_poll.py $TRACER_OPTIONS
