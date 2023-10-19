#!/usr/bin/env bash

set -eo pipefail
set -x

# Find and change to repo root directory
OS=$(uname)
if [[ "$OS" == "Darwin" ]]; then
	# OSX uses BSD readlink
	BASEDIR="$(dirname "$0")"
else
	BASEDIR=$(readlink -e "$(dirname "$0")")
fi
cd "${BASEDIR}/../.." || exit 1

(
cd monitoring || exit 1
make image
)

CORE_SERVICE_CONTAINER="local_infra-dss-1"
OAUTH_CONTAINER="local_infra-oauth-1"
declare -a localhost_containers=("$CORE_SERVICE_CONTAINER" "$OAUTH_CONTAINER")

for container_name in "${localhost_containers[@]}"; do
	if [ "$( docker container inspect -f '{{.State.Status}}' "$container_name" )" == "running" ]; then
		echo "$container_name available!"
	else
		echo "Error: $container_name not running. Execute 'build/dev/run_locally.sh up' before running monitoring/prober/run_locally.sh";
		exit 1;
	fi
done

OUTPUT_DIR="monitoring/prober/output"
mkdir -p "$OUTPUT_DIR"

if ! docker run \
	-u "$(id -u):$(id -g)" \
	--network interop_ecosystem_network \
	-v "$(pwd)/$OUTPUT_DIR:/app/$OUTPUT_DIR" \
	-w /app/monitoring/prober \
	interuss/monitoring \
	pytest \
	"${1:-.}" \
	-rsx \
	--junitxml="/app/$OUTPUT_DIR/e2e_test_result" \
	--dss-endpoint http://dss.uss1.localutm \
	--rid-auth "DummyOAuth(http://oauth.authority.localutm:8085/token,sub=fake_uss)" \
	--rid-v2-auth "DummyOAuth(http://oauth.authority.localutm:8085/token,sub=fake_uss)" \
	--scd-auth1 "DummyOAuth(http://oauth.authority.localutm:8085/token,sub=fake_uss)" \
	--scd-auth2 "DummyOAuth(http://oauth.authority.localutm:8085/token,sub=fake_uss2)"	\
	--scd-api-version 1.0.0; then

    if [ "$CI" == "true" ]; then
        echo "=== END OF TEST RESULTS ==="
        echo "Dumping core-service logs"
        docker logs "$CORE_SERVICE_CONTAINER"
    fi
    echo "Prober did not succeed."
    exit 1
else
    echo "Prober succeeded."
fi
