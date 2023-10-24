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
cd "${BASEDIR}/.." || exit 1

TAG="${1:-interuss/monitoring}"

docker image build \
    -f monitoring/Dockerfile \
    -t "${TAG}" \
    --build-arg version="$(scripts/git/version.sh monitoring --long)" \
    --build-arg commit_hash="$(git rev-parse HEAD)" \
    . \
  || exit 1
echo "File created by monitoring/build.sh to keep track of the latest build run date time." > monitoring/image
