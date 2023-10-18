"""Simple script to extract a field from a JSON representation on stdin."""

import json
import sys


with open(sys.argv[2], "r") as f:
    try:
        obj = json.load(f)
    except ValueError as e:
        raise ValueError(f"Unable to load JSON from {sys.argv[2]}: {e}")

fields = sys.argv[1].split(".")
for field in fields:
    if field == "*":
        obj = obj[next(iter(obj.keys()))]
    else:
        try:
            obj = obj[field]
        except KeyError:
            raise ValueError(
                f"Could not find field '{field}' in '{sys.argv[1]}' for {sys.argv[2]}; available keys: {list(obj.keys())}"
            )
print(obj)
