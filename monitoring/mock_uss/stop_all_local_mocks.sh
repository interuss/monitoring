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

RID_VERSION=${RID_VERSION:-"F3411-19"}
RID_EXT=""
if [ "$RID_VERSION" = "F3411-22a" ]; then
	RID_EXT="_v22a"
fi

docker container rm -f mock_uss_scdsc mock_uss_ridsp${RID_EXT} mock_uss_riddp${RID_EXT} mock_uss_geoawareness mock_uss_atproxy_client mock_uss_tracer${RID_EXT}