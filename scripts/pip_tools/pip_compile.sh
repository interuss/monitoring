#!/usr/bin/env bash

OS=$(uname)
if [[ $OS == "Darwin" ]]; then
	# OSX uses BSD readlink
	BASEDIR="$(dirname "$0")"
else
	BASEDIR=$(readlink -e "$(dirname "$0")")
fi

cd "${BASEDIR}" || exit

cd ../.. || exit

docker image build -f build/dev/pip_tools.Dockerfile build/dev/ -t interuss/pip_tools

docker container run \
	-v "$(pwd):/repo" \
	-w /repo \
	interuss/pip_tools \
  pip-compile "$@"
