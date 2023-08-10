#!/bin/sh

# This startup script is meant to be invoked from within a Docker container
# started by docker-compose.yaml, not on a local system.

if ls /var/dss_component_coordination/scd_bootstrap > /dev/null 2>&1; then
  echo "SCD DB is already set up; no need to run bootstrapper."
  exit 0
else
  echo "Allowing time for CRDB node to come up..."
  sleep 3

  echo "Bootstrapping SCD DB..."
  /usr/bin/db-manager \
    --schemas_dir /db-schemas/scd \
    --db_version "latest" \
    --cockroach_host crdb

  echo "SCD DB bootstrapping complete; notifying other containers..."
  touch /var/dss_component_coordination/scd_bootstrap
fi
