#!/usr/bin/env python3

import argparse
import json
import os
import re
import sys

from jinja2 import Environment, FileSystemLoader


def load_routes():
    routes_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "dss_routes.json"
    )
    if not os.path.exists(routes_path):
        raise RuntimeError(
            f"Routes file {routes_path} not found. Please run enumerate_dss_routes.py first."
        )
    with open(routes_path) as f:
        routes = json.load(f)
    for r in routes:
        r["compiled"] = re.compile(r["pattern"])
    return routes


def match_route(method, path, routes):
    for r in routes:
        if r["method"] == method and r["compiled"].match(path):
            return r
    return None


def resolve_path(cli_path):
    if os.path.isabs(cli_path):
        return cli_path
    if os.path.exists(cli_path):
        return os.path.abspath(cli_path)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, cli_path)


def obfuscate_ip(ip_str, ip_map):
    if not ip_str:
        return "null"
    host = ip_str
    port = None
    if ":" in ip_str:
        parts = ip_str.rsplit(":", 1)
        if parts[1].isdigit():
            host = parts[0]
            port = parts[1]
            if host.startswith("[") and host.endswith("]"):
                host = host[1:-1]

    if host not in ip_map:
        ip_map[host] = f"ip{len(ip_map) + 1}"

    obfuscated_host = ip_map[host]
    if port:
        return f"{obfuscated_host}:{port}"
    return obfuscated_host


def obfuscate_req_sub(sub_val, sub_map):
    if not sub_val:
        return "null"
    if sub_val not in sub_map:
        sub_map[sub_val] = f"sub{len(sub_map) + 1}"
    return sub_map[sub_val]


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
    parser.add_argument(
        "--obfuscate",
        action="append",
        choices=["peer_address", "req_sub"],
        help="Keys to obfuscate in the output (can be specified multiple times)",
    )
    args = parser.parse_args()

    input_path = resolve_path(args.input)
    output_path = resolve_path(args.output)

    print("Loading DSS routes from dss_routes.json...")
    try:
        routes = load_routes()
    except Exception as e:
        print(f"Error loading routes: {e}", file=sys.stderr)
        return
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

    # Mappings for obfuscation
    ip_map = {}
    sub_map = {}
    obfuscate_keys = args.obfuscate or []

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

            hover_parts = [
                f"Origin: {origin}",
                f"Handler: {handler_name}",
            ]

            standard_fields = [
                "timestamp",
                "method",
                "path",
                "proto",
                "status_code",
                "duration_ms",
                "peer_address",
                "req_sub",
            ]

            for field in standard_fields:
                if field in log:
                    val = log[field]
                    if (
                        field == "peer_address"
                        and "peer_address" in obfuscate_keys
                        and val
                    ):
                        val = obfuscate_ip(val, ip_map)
                    elif field == "req_sub" and "req_sub" in obfuscate_keys and val:
                        val = obfuscate_req_sub(val, sub_map)

                    if val is None:
                        val_str = "null"
                    elif isinstance(val, float):
                        val_str = f"{val:.3f}"
                    elif isinstance(val, bool):
                        val_str = "true" if val else "false"
                    else:
                        val_str = str(val)

                    hover_parts.append(f"{field}: {val_str}")

            for k, v in log.items():
                if k not in standard_fields:
                    val_str = "null" if v is None else str(v)
                    hover_parts.append(f"{k}: {val_str}")

            hover = "<br>".join(hover_parts)

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
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "../templates")
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
