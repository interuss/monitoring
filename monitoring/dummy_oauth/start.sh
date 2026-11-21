#!/usr/bin/env sh
set -eu

exec gunicorn --preload --bind "0.0.0.0:${DUMMY_OAUTH_PORT:-8085}" \
    'monitoring.dummy_oauth.app:create_app()' "$@"
