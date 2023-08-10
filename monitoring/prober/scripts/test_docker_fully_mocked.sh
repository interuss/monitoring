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

function collect_logs() {
  mkdir -p logs/prober
  build/dev/run_locally.sh logs --timestamps > logs/prober/local_infra.log 2>&1
}

function cleanup() {
  echo "Clean up"
  echo "============="
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

echo "Run the standard local tests."
echo "============="
monitoring/prober/run_locally.sh
