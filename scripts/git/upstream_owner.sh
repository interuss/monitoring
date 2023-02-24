#!/usr/bin/env bash

# This script attempts to print the organization of the upstream repository.

# The following strategies will be used to determine the organization name:
# 1. If a remote named `origin` exists, the organization name will be extracted from the
# remote URL assuming the format below.
# 2. If a remote named `interuss` exists, the organization name will be extracted from the
# remote URL assuming the format below.
# 3. If the upstream of the current branch exists, the organization name will be set to the
# upstream repo name.
# 4. Otherwise, the default organization name of "unknown" will be printed.

# The expected URL formats for remote URLs are:
# 1. git@github.com:interuss/monitoring.git
# 2. git@github.com/interuss/monitoring.git
# 3. https://github.com/interuss/monitoring.git

# Determine what remote this branch is tracking, in case `origin` and `interuss` don't exist
BACKUP_REPO="https://github.com/$(git rev-parse --abbrev-ref @\{upstream\} 2> /dev/null || echo unknown/_)"

UPSTREAM_REPO=$(git remote get-url origin 2> /dev/null || git remote get-url interuss 2> /dev/null || echo "$BACKUP_REPO")
# Replace `:` by `/` to handle git@github.com:interuss/monitoring.git remote reference.
UPSTREAM_REPO=${UPSTREAM_REPO//:/\/}
# Remove hostname part
UPSTREAM_OWNER=$(dirname "${UPSTREAM_REPO#*github.com/*}")

echo "$UPSTREAM_OWNER"
