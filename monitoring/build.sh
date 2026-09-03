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

if [[ "$1" == "dev" ]]; then
  IMAGE_VARIANT="dev"
  TAG="${2:-interuss/monitoring}"
elif [[ "$1" == "normal" ]]; then
  IMAGE_VARIANT="normal"
  TAG="${2:-interuss/monitoring}"
else
  IMAGE_VARIANT="normal"
  TAG="${1:-interuss/monitoring}"
fi
VERSION_STR=$(scripts/git/get_version.py --format pep440)
COMMIT_HASH=$(scripts/git/get_version.py --format commitsha1)

if [[ "${IMAGE_VARIANT}" == "normal" ]]; then
  DOCKER_TAG="${TAG}"
else
  DOCKER_TAG="${TAG}-dev"
fi

echo "=== InterUSS docker ${IMAGE_VARIANT} image build ==="
echo "Version:     ${VERSION_STR}"
echo "Docker tag:  ${DOCKER_TAG}"
echo "Commit hash: ${COMMIT_HASH}"
echo "======================================"

if [[ "${IMAGE_VARIANT}" == "normal" ]]; then
  docker image build \
      -f monitoring/Dockerfile \
      -t "${DOCKER_TAG}" \
      --build-arg version="${VERSION_STR}" \
      --build-arg commit_hash="${COMMIT_HASH}" \
      . \
    || exit 1

  echo "File created by monitoring/build.sh to keep track of the latest normal image build run date time." > monitoring/image

else
  docker image build \
      -f monitoring/Dockerfile \
      -t "${DOCKER_TAG}" \
      --build-arg BASE_STAGE=dev-dependencies \
      --build-arg version="${VERSION_STR}" \
      --build-arg commit_hash="${COMMIT_HASH}" \
      . \
    || exit 1

  echo "File created by monitoring/build.sh to keep track of the latest dev image build run date time." > monitoring/image-dev
fi
