#!/usr/bin/env bash

set -eo pipefail

error_found=false # It's good practice to initialize your flag

# Check for 'v19' references in netrid v22a scenario documents
# '|| true' to prevent 'set -e' from exiting if grep finds nothing
filesv22a=$(find ./scenarios/astm/netrid/v22a -name '*.md' -exec grep -l 'v19' {} + || true)
if [ -n "$filesv22a" ]; then
    echo "Error: Found netrid v22a scenario document containing a 'v19' reference:"
    echo "$filesv22a"
    error_found=true
fi

# Check for 'v22a' references in netrid v19 scenario documents
# '|| true' to prevent 'set -e' from exiting if grep finds nothing
filesv19=$(find ./scenarios/astm/netrid/v19 -name '*.md' -exec grep -l 'v22a' {} + || true)
if [ -n "$filesv19" ]; then
    echo "Error: Found netrid v19 scenario document containing a 'v22a' reference:"
    echo "$filesv19"
    error_found=true
fi

# Error if we found any file
if [ "$error_found" = true ]; then
    exit 1
fi

# Otherwise all is good
echo "All checks passed."
exit 0
