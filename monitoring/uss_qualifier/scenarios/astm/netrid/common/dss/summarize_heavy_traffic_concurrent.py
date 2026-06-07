#!/usr/bin/env python3
"""
Summarizes the performance of HeavyTrafficConcurrent scenarios from a TestRunReport.

Example command to run this script (from the repo root):
PYTHONPATH=. uv run python monitoring/uss_qualifier/scenarios/astm/netrid/common/dss/summarize_heavy_traffic_concurrent.py --report monitoring/uss_qualifier/output/netrid_concurrency/report.json --output monitoring/uss_qualifier/output/netrid_concurrency/summary.html
"""

import argparse
import json
import os
import statistics
from typing import List

from implicitdict import ImplicitDict
from monitoring.uss_qualifier.reports import jinja_env
from monitoring.uss_qualifier.reports.report import (
    TestRunReport,
    TestScenarioReport,
    TestSuiteActionReport,
)


def find_heavy_traffic_concurrent_scenarios(
    action_report: TestSuiteActionReport,
) -> List[TestScenarioReport]:
    """Recursively search for HeavyTrafficConcurrent scenarios in the action report."""
    scenarios = []
    if "test_scenario" in action_report and action_report.test_scenario:
        if action_report.test_scenario.scenario_type.endswith(
            ".HeavyTrafficConcurrent"
        ):
            scenarios.append(action_report.test_scenario)
    elif "test_suite" in action_report and action_report.test_suite:
        for action in action_report.test_suite.actions:
            scenarios.extend(find_heavy_traffic_concurrent_scenarios(action))
    elif "action_generator" in action_report and action_report.action_generator:
        for action in action_report.action_generator.actions:
            scenarios.extend(find_heavy_traffic_concurrent_scenarios(action))
    return scenarios


def get_dss_participant_id(scenario: TestScenarioReport) -> str:
    """Extract participant_id of the DSS under test in the scenario."""
    # Attempt to extract participant ID from recorded queries
    for case in scenario.cases:
        for step in case.steps:
            queries = step.queries if ("queries" in step and step.queries is not None) else []

            for q in queries:
                if q.participant_id:
                    return q.participant_id

    # Fallback to resource_origins if queries not available
    if (
        "resource_origins" in scenario
        and scenario.resource_origins
        and "dss" in scenario.resource_origins
    ):
        return f"dss ({scenario.resource_origins['dss']})"

    return "unknown"


def extract_metrics(scenario: TestScenarioReport) -> dict:
    """Extract and calculate QPS, latency, and success statistics for the key steps."""
    metrics = {}

    step_mapping = {
        "Create ISA concurrently": "isa_creation",
        "Get ISAs concurrently": "created_isa_query",
        "Delete ISAs concurrently": "isa_deletion",
        "Access Deleted ISAs": "deleted_isa_query",
    }

    success_codes = {
        "isa_creation": {200, 201},
        "created_isa_query": {200},
        "isa_deletion": {200},
        "deleted_isa_query": {404},
    }

    for case in scenario.cases:
        for step in case.steps:
            if step.name in step_mapping:
                op = step_mapping[step.name]
                queries = step.queries if ("queries" in step and step.queries is not None) else []
                if not queries:
                    continue

                t_start = step.start_time.datetime
                t_end = step.end_time.datetime if step.end_time else t_start
                duration_s = (t_end - t_start).total_seconds()

                total_count = len(queries)
                success_count = sum(
                    1 for q in queries if q.status_code in success_codes[op]
                )

                qps = total_count / duration_s if duration_s > 0 else 0.0

                latencies = [
                    q.response.elapsed_s
                    for q in queries
                    if q.response.elapsed_s is not None
                ]
                if latencies:
                    min_ms = min(latencies) * 1000
                    max_ms = max(latencies) * 1000
                    median_ms = statistics.median(latencies) * 1000
                else:
                    min_ms = median_ms = max_ms = 0.0

                success_rate = (
                    (success_count / total_count * 100) if total_count > 0 else 0.0
                )

                metrics[op] = {
                    "qps": qps,
                    "min_ms": min_ms,
                    "median_ms": median_ms,
                    "max_ms": max_ms,
                    "success_count": success_count,
                    "total_count": total_count,
                    "success_rate": success_rate,
                }
    return metrics


def main():
    parser = argparse.ArgumentParser(
        description="Summarize HeavyTrafficConcurrent performance from report.json"
    )
    parser.add_argument(
        "--report",
        required=True,
        help="Path to raw report.json (TestRunReport)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to generate the HTML summary file",
    )
    args = parser.parse_args()

    print(f"Loading report from: {args.report}")
    with open(args.report, "r") as f:
        raw_report = json.load(f)
    report = ImplicitDict.parse(raw_report, TestRunReport)

    scenarios = find_heavy_traffic_concurrent_scenarios(report.report)
    print(f"Found {len(scenarios)} HeavyTrafficConcurrent scenario(s)")

    rows = []
    for scenario in scenarios:
        part_id = get_dss_participant_id(scenario)
        metrics = extract_metrics(scenario)
        rows.append(
            {
                "participant_id": part_id,
                "scenario_name": scenario.name,
                "start_time": scenario.start_time,
                "metrics": metrics,
            }
        )

    # Render template using Jinja2
    template = jinja_env.get_template("heavy_traffic_concurrent/summary.html")
    rendered_html = template.render(rows=rows)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w") as f:
        f.write(rendered_html)

    print(f"Summary HTML generated successfully at: {args.output}")


if __name__ == "__main__":
    main()
