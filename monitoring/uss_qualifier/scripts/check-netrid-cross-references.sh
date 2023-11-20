#!/usr/bin/env bash

# Check for 'v19' references in netrid v22a scenario documents
filesv22a=$(find ./scenarios/astm/netrid/v22a -name '*.md' -exec grep -l 'v19' {} +)
if [ -n "$filesv22a" ]; then
    echo "Error: Found netrid v22a scenario document containing a 'v19' reference:"
    echo "$filesv22a"
    error_found=true
fi

# Check for 'v22a' references in netrid v19 scenario documents
filesv19=$(find ./scenarios/astm/netrid/v19 -name '*.md' -exec grep -l 'v22a' {} +)
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
exit 0
