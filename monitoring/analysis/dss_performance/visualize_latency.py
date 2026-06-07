#!/usr/bin/env python3

import argparse
import glob
import json
import os
import re

from jinja2 import Environment, FileSystemLoader


def find_workspace_root():
    curr = os.path.abspath(os.path.dirname(__file__))
    while curr and curr != "/":
        if os.path.exists(os.path.join(curr, "dss")) and os.path.exists(
            os.path.join(curr, "monitoring")
        ):
            return curr
        curr = os.path.dirname(curr)
    raise RuntimeError(
        "Could not find workspace root containing dss and monitoring directories"
    )


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
            "compiled": re.compile(r"^/healthy$"),
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
                    "compiled": re.compile(pattern_str),
                }
            )
    return routes


def match_route(method, path, routes):
    for r in routes:
        if r["method"] == method and r["compiled"].match(path):
            return r
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Visualize DSS latency performance logs."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="acquired_logs.json",
        help="Path to JSON output of acquire_logs.py",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="latency_visualization.html",
        help="Path to write the standalone HTML output",
    )
    args = parser.parse_args()

    workspace_root = find_workspace_root()
    dss_dir = os.path.join(workspace_root, "dss")

    # Resolve paths relative to workspace root if they are not absolute
    input_path = (
        args.input
        if os.path.isabs(args.input)
        else os.path.join(
            workspace_root, "monitoring/monitoring/analysis/dss_performance", args.input
        )
    )
    output_path = (
        args.output
        if os.path.isabs(args.output)
        else os.path.join(
            workspace_root,
            "monitoring/monitoring/analysis/dss_performance",
            args.output,
        )
    )

    print("Loading routes from DSS Go router code...")
    routes = load_dss_routes(dss_dir)
    print(f"Loaded {len(routes)} handlers/routes.")

    print(f"Loading logs from {input_path}...")
    if not os.path.exists(input_path):
        print(f"Error: log file {input_path} does not exist.")
        return

    with open(input_path) as f:
        log_data = json.load(f)

    # We will group log points by (origin, category, handler_full_name)
    # where handler_full_name is e.g. "PUT /rid/v2/dss/identification_service_areas/{id}"
    trace_groups = {}

    origins = log_data.get("origins", {})
    total_logs = 0
    matched_logs = 0

    for origin, logs in origins.items():
        for log in logs:
            total_logs += 1
            method = log.get("method")
            path = log.get("path")
            timestamp = log.get("timestamp")
            duration_ms = log.get("duration_ms")

            if not method or not path or not timestamp or duration_ms is None:
                continue

            route = match_route(method, path, routes)
            if route:
                matched_logs += 1
                category = route["category"]
                handler_name = f"{method} {route['path_template']}"
            else:
                category = "other"
                handler_name = f"{method} {path}"

            group_key = (origin, category, handler_name)
            if group_key not in trace_groups:
                trace_groups[group_key] = {"x": [], "y": [], "text": []}

            status_code = log.get("status_code", "N/A")
            req_sub = log.get("req_sub") or "N/A"
            peer_address = log.get("peer_address") or "N/A"

            hover = (
                f"Origin: {origin}<br>"
                f"Handler: {handler_name}<br>"
                f"Time: {timestamp}<br>"
                f"Latency: {duration_ms:.3f} ms<br>"
                f"Status: {status_code}<br>"
                f"Client: {req_sub}<br>"
                f"Peer: {peer_address}"
            )

            trace_groups[group_key]["x"].append(timestamp)
            trace_groups[group_key]["y"].append(duration_ms)
            trace_groups[group_key]["text"].append(hover)

    print(f"Matched {matched_logs}/{total_logs} log entries.")

    # Flatten and build Plotly traces
    traces = []
    sidebar_data = {"origins": {}}

    # Sort groups by (origin, category, handler_name) for stable layout
    sorted_group_keys = sorted(trace_groups.keys())

    for idx, key in enumerate(sorted_group_keys):
        origin, category, handler_name = key
        group_data = trace_groups[key]

        # Create a Plotly trace
        trace = {
            "name": f"{origin}: {handler_name}",
            "x": group_data["x"],
            "y": group_data["y"],
            "text": group_data["text"],
            "hoverinfo": "text",
        }
        traces.append(trace)

        # Populate sidebar structure
        if origin not in sidebar_data["origins"]:
            sidebar_data["origins"][origin] = {"categories": {}}

        categories_dict = sidebar_data["origins"][origin]["categories"]
        if category not in categories_dict:
            categories_dict[category] = []

        categories_dict[category].append(
            {"handler_name": handler_name, "trace_index": idx}
        )

    # Sort origins, categories, and handlers for alphabetical consistency
    sorted_origins = sorted(sidebar_data["origins"].keys())
    ordered_sidebar = {"origins": {}}
    for origin in sorted_origins:
        categories = sidebar_data["origins"][origin]["categories"]
        sorted_categories = sorted(categories.keys())
        ordered_sidebar["origins"][origin] = {"categories": {}}
        for cat in sorted_categories:
            ordered_sidebar["origins"][origin]["categories"][cat] = sorted(
                categories[cat], key=lambda h: h["handler_name"]
            )

    sidebar_data = ordered_sidebar
    traces_json = json.dumps(traces)

    # Load Jinja template
    templates_dir = os.path.abspath(
        os.path.join(workspace_root, "monitoring/monitoring/analysis/templates")
    )
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template("visualize_latency.html")

    html_out = template.render(sidebar_data=sidebar_data, traces_json=traces_json)

    print(f"Writing visualization HTML to {output_path}...")
    with open(output_path, "w") as f:
        f.write(html_out)

    print("Done! Open the HTML file in your browser to inspect.")


if __name__ == "__main__":
    main()
