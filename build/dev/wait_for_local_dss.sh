#!/bin/bash

compose_version=$(docker compose version --short | awk '{print 2}')
if [[ $compose_version == 1 ]]; then
  # Docker Compose V1
  OAUTH_CONTAINER="dss_sandbox_local-dss-dummy-oauth_1"
  CORE_SERVICE_CONTAINER="dss_sandbox_local-dss-core-service_1"
elif [[ $compose_version == 2 ]]; then
  # Docker Compose V2
  OAUTH_CONTAINER="dss_sandbox-local-dss-dummy-oauth-1"
  CORE_SERVICE_CONTAINER="dss_sandbox-local-dss-core-service-1"
else
  # Unsupported Docker Version.
  echo "Unsupported Docker Compose version: $compose_version"
  exit 1
fi

declare -a localhost_containers=("$OAUTH_CONTAINER" "$CORE_SERVICE_CONTAINER")

for container_name in "${localhost_containers[@]}"; do
  last_message=""
  while true; do
    if [ "$( docker container inspect -f '{{.State.Status}}' "${container_name}" 2>/dev/null)" = "running" ]; then
      break
    fi
    new_message="Waiting for ${container_name} container to start..."
    if [ "${new_message}" = "${last_message}" ]; then
      printf "."
    else
      printf '%s' "${new_message}"
      last_message="${new_message}"
    fi
    sleep 3
  done
  if [ -n "${last_message}" ]; then
    echo ""
  fi
done

last_message=""
while true; do
  health_status="$( docker container inspect -f '{{.State.Health.Status}}' "${CORE_SERVICE_CONTAINER}" )"
    if [ "${health_status}" = "healthy" ]; then
      break
    else
      new_message="Waiting for ${CORE_SERVICE_CONTAINER} to be available (currently ${health_status})..."
      if [ "${new_message}" = "${last_message}" ]; then
        printf "."
      else
        printf '%s' "${new_message}"
        last_message="${new_message}"
      fi
      sleep 3
    fi
done
if [ -n "${last_message}" ]; then
  echo ""
fi

echo "Local DSS instance is now available."
