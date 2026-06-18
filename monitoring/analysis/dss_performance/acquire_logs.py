#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime

# Regex to parse the HTTP request line from the 'msg' field:
# E.g. "GET /v1/dss/operational_intent_references/1234 HTTP/1.1" or "POST /v1/dss/subscriptions HTTP/2"
HTTP_MSG_PATTERN = re.compile(r"^([A-Z]+)\s+(\S+)\s+(HTTP/\S+)$")


class FileLock:
    """A simple zero-dependency file lock implementation for Unix systems."""

    def __init__(self, filepath: str, timeout: int = 15):
        self.lockfile = f"{filepath}.lock"
        self.timeout = timeout
        self.fd = None

    def __enter__(self):
        start_time = time.time()
        while True:
            try:
                # Open with O_CREAT and O_EXCL is atomic on Unix
                self.fd = os.open(self.lockfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break
            except FileExistsError:
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(
                        f"Could not acquire lock on {self.lockfile} within {self.timeout} seconds."
                    )
                time.sleep(0.1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fd is not None:
            os.close(self.fd)
            try:
                os.remove(self.lockfile)
            except OSError:
                pass


def parse_duration_to_ms(d_str) -> float:
    """Parses a Go-style duration string (e.g. '3.5ms', '120µs', '2s') to milliseconds."""
    if isinstance(d_str, (int, float)):
        return float(d_str)

    if not isinstance(d_str, str):
        return 0.0

    # Parse components of duration: e.g. "1.5s", "120µs", etc.
    pattern = re.compile(r"([\d\.]+)(ns|µs|us|ms|s|m|h)")
    matches = pattern.findall(d_str)
    if not matches:
        try:
            return float(d_str)
        except ValueError:
            return 0.0

    total_ms = 0.0
    units = {
        "ns": 1e-6,
        "µs": 1e-3,
        "us": 1e-3,
        "ms": 1.0,
        "s": 1000.0,
        "m": 60000.0,
        "h": 3600000.0,
    }
    for val, unit in matches:
        total_ms += float(val) * units.get(unit, 0.0)
    return total_ms


def parse_http_log(entry: dict) -> dict | None:
    """Parses a raw Zap JSON log entry and extracts HTTP performance metrics if applicable."""
    if not isinstance(entry, dict):
        return None

    # Identify if this is the HTTP middleware log entry of interest
    if "resp_status_code" not in entry or "duration" not in entry:
        return None

    msg = entry.get("msg", "")
    match = HTTP_MSG_PATTERN.match(msg)
    if not match:
        return None

    method, path, proto = match.groups()

    # Normalize duration to milliseconds
    duration_ms = parse_duration_to_ms(entry.get("duration"))

    # Determine timestamp (prefer start_time from http middleware, fallback to ts or timestamp)
    timestamp = entry.get("start_time") or entry.get("ts") or entry.get("timestamp")
    if isinstance(timestamp, (int, float)):
        timestamp = datetime.fromtimestamp(timestamp).isoformat() + "Z"
    elif not isinstance(timestamp, str):
        timestamp = datetime.utcnow().isoformat() + "Z"

    return {
        "timestamp": timestamp,
        "method": method,
        "path": path,
        "proto": proto,
        "status_code": entry["resp_status_code"],
        "duration_ms": duration_ms,
        "peer_address": entry.get("peer_address"),
        "req_sub": entry.get("req_sub"),
    }


def parse_json_line(line: str) -> dict | None:
    """Extracts and parses the first JSON object found in a line."""
    line = line.strip()
    idx = line.find("{")
    if idx == -1:
        return None
    try:
        entry = json.loads(line[idx:])
    except json.JSONDecodeError:
        return None

    if not isinstance(entry, dict):
        return None

    # If there is a prefix before the JSON block, try to extract the 'msg'
    if idx > 0:
        text_part = line[:idx].strip()
        if text_part:
            parts = [p for p in re.split(r"\t|\s{2,}", text_part) if p]
            if parts:
                # The last part of the console prefix is typically the message
                entry["msg"] = parts[-1]

    return entry


def get_origin_name(
    entry: dict, style: str, fixed_origin: str | None, origin_format: str | None
) -> str:
    """Determines the origin name for a log entry based on style and configuration."""
    if style == "docker":
        return fixed_origin or "docker-container"

    # gcloud style
    labels = entry.get("resource", {}).get("labels", {})
    pod_name = labels.get("pod_name", "unknown-pod")
    container_name = labels.get("container_name", "unknown-container")
    cluster_name = labels.get("cluster_name", "unknown-cluster")
    namespace_name = labels.get("namespace_name", "unknown-namespace")

    fmt = origin_format or fixed_origin or "{pod_name}"

    try:
        return fmt.format(
            pod_name=pod_name,
            container_name=container_name,
            cluster_name=cluster_name,
            namespace_name=namespace_name,
            **labels,
        )
    except Exception:
        return pod_name or container_name or "gcloud-origin"


def parse_gcloud_stdin(stdin_str: str) -> list[dict]:
    """Parses standard input from gcloud as either a JSON array, a single object, or NDJSON."""
    try:
        data = json.loads(stdin_str)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        pass

    # Fallback to reading line-by-line JSON
    entries = []
    for line in stdin_str.splitlines():
        parsed = parse_json_line(line)
        if parsed:
            entries.append(parsed)
    return entries


def main():
    parser = argparse.ArgumentParser(
        description="Normalize and acquire Zap-based DSS logs into a standard format."
    )
    parser.add_argument(
        "--style",
        choices=["docker", "gcloud"],
        required=True,
        help="The style of the input logs. 'docker' reads line-by-line raw console logs. "
        "'gcloud' parses JSON structures containing jsonPayload and resource.labels.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the output file to write/append normalized logs.",
    )
    parser.add_argument(
        "--origin",
        help="For docker style, the fixed origin name. For gcloud, acts as the format template if "
        "--origin-format is not specified.",
    )
    parser.add_argument(
        "--origin-format",
        help="Format template for the origin name in gcloud logs (e.g. '{pod_name}' or '{container_name}').",
    )

    args = parser.parse_args()

    # Read and parse input according to selected style
    new_logs = {}

    if args.style == "docker":
        for line in sys.stdin:
            entry = parse_json_line(line)
            if not entry:
                continue
            parsed = parse_http_log(entry)
            if parsed:
                origin = get_origin_name(
                    entry, "docker", args.origin, args.origin_format
                )
                if origin not in new_logs:
                    new_logs[origin] = []
                new_logs[origin].append(parsed)
    elif args.style == "gcloud":
        stdin_content = sys.stdin.read()
        if not stdin_content.strip():
            print("No input received.", file=sys.stderr)
            sys.exit(0)
        entries = parse_gcloud_stdin(stdin_content)
        for entry in entries:
            # gcloud structured log wraps the actual log inside jsonPayload
            payload = entry.get("jsonPayload")
            if isinstance(payload, dict):
                parsed = parse_http_log(payload)
            else:
                text_payload = entry.get("textPayload")
                if isinstance(text_payload, str):
                    payload_dict = parse_json_line(text_payload)
                    parsed = parse_http_log(payload_dict) if payload_dict else None
                else:
                    parsed = parse_http_log(entry)
            if parsed:
                origin = get_origin_name(
                    entry, "gcloud", args.origin, args.origin_format
                )
                if origin not in new_logs:
                    new_logs[origin] = []
                new_logs[origin].append(parsed)

    if not new_logs:
        print("No matching HTTP server logs found to acquire.")
        sys.exit(0)

    # Ensure output directory exists
    output_dir = os.path.dirname(os.path.abspath(args.output))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Acquire lock and read/write the combined file
    with FileLock(args.output):
        if os.path.exists(args.output):
            try:
                with open(args.output) as f:
                    data = json.load(f)
            except Exception as e:
                print(
                    f"Warning: Failed to parse existing output file: {e}. Re-initializing.",
                    file=sys.stderr,
                )
                data = {}
        else:
            data = {}

        if not isinstance(data, dict):
            data = {}
        if "origins" not in data:
            data["origins"] = {}

        total_added = 0
        for origin, entries in new_logs.items():
            if origin not in data["origins"]:
                data["origins"][origin] = []

            existing_entries = data["origins"][origin]
            # Create a set of signatures to prevent adding exact duplicates
            existing_sigs = {
                (
                    e.get("timestamp"),
                    e.get("method"),
                    e.get("path"),
                    e.get("status_code"),
                    e.get("duration_ms"),
                )
                for e in existing_entries
                if isinstance(e, dict)
            }

            added_for_origin = 0
            for entry in entries:
                sig = (
                    entry.get("timestamp"),
                    entry.get("method"),
                    entry.get("path"),
                    entry.get("status_code"),
                    entry.get("duration_ms"),
                )
                if sig not in existing_sigs:
                    existing_entries.append(entry)
                    existing_sigs.add(sig)
                    added_for_origin += 1

            # Sort entries chronologically
            existing_entries.sort(key=lambda x: x.get("timestamp", ""))
            total_added += added_for_origin
            print(
                f"Origin '{origin}': added {added_for_origin} new entries (total: {len(existing_entries)})"
            )

        if total_added > 0:
            with open(args.output, "w") as f:
                json.dump(data, f, indent=2)
            print(
                f"Successfully wrote {total_added} total new log entries to {args.output}"
            )
        else:
            print(
                "All acquired log entries already existed in the output file. No changes made."
            )


if __name__ == "__main__":
    main()
