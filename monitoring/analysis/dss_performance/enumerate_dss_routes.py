#!/usr/bin/env python3

"""Enumerate DSS routes from Go server.gen.go definitions and save them to JSON.

Prerequisite:
    The user must have the 'dss' repository cloned as a sibling to the
    'monitoring' repository (e.g. at the same parent workspace directory).
"""

import glob
import json
import os
import re
import sys


def find_sibling_dss_dir():
    # This script is located in: monitoring/monitoring/analysis/dss_performance/enumerate_dss_routes.py
    # Sibling dss directory is four levels up, then 'dss'
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    dss_dir = os.path.abspath(os.path.join(curr_dir, "../../../../dss"))
    return dss_dir


def load_dss_routes(dss_dir):
    go_files = glob.glob(os.path.join(dss_dir, "pkg/api/*/server.gen.go"))
    routes = []

    # Add healthy endpoint implicitly
    routes.append(
        {
            "category": "auxv1",
            "method": "GET",
            "pattern": "^/healthy$",
            "path_template": "/healthy",
        }
    )

    for go_file in go_files:
        category = os.path.basename(os.path.dirname(go_file))
        with open(go_file) as f:
            content = f.read()

        router_func_match = re.search(
            r"func MakeAPIRouter\(.*?\).*?{(.*?)^}", content, re.MULTILINE | re.DOTALL
        )
        if not router_func_match:
            continue

        func_content = router_func_match.group(1)
        parts = re.split(r"pattern\s*(?::)?=\s*regexp\.MustCompile\(", func_content)
        for part in parts[1:]:
            pattern_match = re.match(r"^\"([^\"]+)\"", part)
            if not pattern_match:
                continue
            pattern_str = pattern_match.group(1)

            method_match = re.search(r"Method:\s*http\.Method(\w+)", part)
            if not method_match:
                continue
            method = method_match.group(1).upper()

            path_match = re.search(r"Path:\s*\"([^\"]+)\"", part)
            if path_match:
                path_template = path_match.group(1)
            else:
                clean_path = pattern_str.lstrip("^").rstrip("$")
                path_template = re.sub(r"\(\?P<([^>]+)>[^)]+\)", r"{\1}", clean_path)

            routes.append(
                {
                    "category": category,
                    "method": method,
                    "pattern": pattern_str,
                    "path_template": path_template,
                }
            )
    return routes


def main():
    dss_dir = find_sibling_dss_dir()
    if not os.path.exists(dss_dir):
        print(
            f"Error: DSS repository not found at expected sibling location: {dss_dir}",
            file=sys.stderr,
        )
        print(
            "Please ensure you have cloned the 'dss' repository as a sibling to 'monitoring'.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Parsing DSS routes from sibling dss directory: {dss_dir}")
    routes = load_dss_routes(dss_dir)
    print(f"Found {len(routes)} routes.")

    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "dss_routes.json"
    )
    print(f"Writing routes to {output_path}...")
    with open(output_path, "w") as f:
        json.dump(routes, f, indent=2)

    print("Done!")


if __name__ == "__main__":
    main()
