#!/usr/bin/env bash

set -eo pipefail
set -o xtrace

# Find and change to repo root directory
OS=$(uname)
if [[ "$OS" == "Darwin" ]]; then
	# OSX uses BSD readlink
	BASEDIR="$(dirname "$0")"
else
	BASEDIR=$(readlink -e "$(dirname "$0")")
fi
cd "${BASEDIR}/../../.." || exit 1

echo "Ensure the environment is clean"
echo "============="
make down-locally
make stop-uss-mocks

function collect_logs() {
  echo "Collect local logs"
  echo "============="
  make collect-local-logs
}

function cleanup() {
  echo "Clean up"
  echo "============="
  make stop-uss-mocks
  make down-locally
}

function on_exit() {
    collect_logs
	cleanup
}

function on_sigint() {
    collect_logs
	cleanup
	exit
}

trap on_exit   EXIT
trap on_sigint SIGINT

echo "Start mock system"
echo "============="
make start-locally
make start-uss-mocks

CONFIG_NAME=${CONFIG_NAME:-""}
echo "Selecting configuration"
echo "============="
echo "CONFIG_NAME: $CONFIG_NAME"


echo "Run the standard local tests."
echo "============="
monitoring/uss_qualifier/run_locally.sh "$CONFIG_NAME"
