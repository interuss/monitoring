#!/usr/bin/env bash

# This script builds and pushes the InterUSS monitoring docker image and may be
# run from any working directory.  If DOCKER_URL is present, it will both
# build the versioned monitoring image and push it to the DOCKER_URL remote.

set -eo pipefail

OS=$(uname)
if [[ "$OS" == "Darwin" ]]; then
	# OSX uses BSD readlink
	BASEDIR="$(dirname "$0")/.."
else
	BASEDIR=$(readlink -e "$(dirname "$0")/..")
fi
cd "${BASEDIR}"

VERSION=$(./scripts/git/version.sh monitoring)

if [[ -z "${DOCKER_URL}" ]]; then
  echo "DOCKER_URL environment variable is not set; building image to interuss/monitoring..."
  ./monitoring/build.sh

  echo "DOCKER_URL environment variable was not set; built image to interuss/monitoring"
else
  echo "Building image ${DOCKER_URL}/monitoring:${VERSION}"
  ./monitoring/build.sh "${DOCKER_URL}/monitoring:${VERSION}"

  echo "Pushing docker image ${DOCKER_URL}/monitoring:${VERSION}..."
  docker image push "${DOCKER_URL}/monitoring:${VERSION}"

  echo "Built and pushed docker image ${DOCKER_URL}/monitoring:${VERSION}"
fi
