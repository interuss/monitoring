#!/bin/bash

# Find and change to repo root directory
OS=$(uname)
if [[ "$OS" == "Darwin" ]]; then
	# OSX uses BSD readlink
	BASEDIR="$(dirname "$0")"
else
	BASEDIR=$(readlink -e "$(dirname "$0")")
fi
cd "${BASEDIR}/../.." || exit 1

RID_VERSION=${RID_VERSION:-"F3411-22a"}
RID_EXT=""
if [ "$RID_VERSION" = "F3411-19" ]; then
	RID_EXT="_v19"
fi

docker container rm -f \
mock_uss_scdsc_a \
mock_uss_scdsc_b \
mock_uss_ridsp${RID_EXT} \
mock_uss_riddp${RID_EXT} \
mock_uss_geoawareness \
mock_uss_atproxy_client \
mock_uss_tracer${RID_EXT}