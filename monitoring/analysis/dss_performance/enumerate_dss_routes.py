#!/usr/bin/env python3

"""Enumerate DSS routes from Go server.gen.go definitions and save them to JSON."""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

# Fallback categories to query if the GitHub contents API fails
FALLBACK_CATEGORIES = ["auxv1", "ridv1", "ridv2", "scdv1", "versioningv1"]


def sanitize_ref_for_filename(ref):
    return re.sub(r"[^a-zA-Z0-9._-]", "_", ref)


def parse_server_go_content(content, category):
    routes = []
    router_func_match = re.search(
        r"func MakeAPIRouter\(.*?\).*?{(.*?)^}", content, re.MULTILINE | re.DOTALL
    )
    if not router_func_match:
        return routes

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


def get_routes(ref):
    """Get routes for the given ref, loading from cache if available, otherwise fetching from GitHub."""
    sanitized_ref = sanitize_ref_for_filename(ref)
    cache_dir = os.path.dirname(os.path.abspath(__file__))
    cache_path = os.path.join(cache_dir, f"dss_routes.{sanitized_ref}.json")

    # Try loading from cache first
    if os.path.exists(cache_path):
        print(f"Loading DSS routes from cache: {cache_path}")
        with open(cache_path) as f:
            return json.load(f)

    # Otherwise fetch from GitHub
    print(f"Cache not found. Fetching DSS routes from GitHub for ref '{ref}'...")
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

    # 1. Fetch categories
    categories = None
    api_url = f"https://api.github.com/repos/interuss/dss/contents/pkg/api?ref={ref}"
    req = urllib.request.Request(
        api_url, headers={"User-Agent": "Interuss-DSS-Route-Enumerator"}
    )
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            categories = [item["name"] for item in data if item["type"] == "dir"]
    except Exception as e:
        print(
            f"Warning: Failed to fetch categories from GitHub API: {e}. Using fallback categories list.",
            file=sys.stderr,
        )
        categories = FALLBACK_CATEGORIES

    # 2. Fetch server.gen.go for each category
    for category in categories:
        raw_url = f"https://raw.githubusercontent.com/interuss/dss/{ref}/pkg/api/{category}/server.gen.go"
        req = urllib.request.Request(
            raw_url, headers={"User-Agent": "Interuss-DSS-Route-Enumerator"}
        )
        try:
            with urllib.request.urlopen(req) as response:
                content = response.read().decode("utf-8")
            category_routes = parse_server_go_content(content, category)
            routes.extend(category_routes)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Silently ignore if server.gen.go does not exist for this category
                continue
            else:
                print(
                    f"Warning: Failed to fetch routes for category {category}: {e}",
                    file=sys.stderr,
                )
        except Exception as e:
            print(
                f"Warning: Failed to fetch routes for category {category}: {e}",
                file=sys.stderr,
            )

    # Save to cache
    print(f"Writing routes cache to {cache_path}...")
    with open(cache_path, "w") as f:
        json.dump(routes, f, indent=2)

    return routes


def main():
    parser = argparse.ArgumentParser(
        description="Enumerate DSS routes from GitHub repo or local cache."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--tag", help="Git tag in the interuss/dss repo to fetch routes for"
    )
    group.add_argument(
        "--commit",
        help="Git commit hash in the interuss/dss repo to fetch routes for",
    )
    args = parser.parse_args()

    ref = args.tag or args.commit or "master"
    try:
        routes = get_routes(ref)
        print(f"Successfully processed {len(routes)} routes for ref '{ref}'.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
