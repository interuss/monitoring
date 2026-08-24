from __future__ import annotations

import json
import os
import re
from typing import Any

from loguru import logger

from monitoring.benchmarker.artifacts.timeline import jinja_env
from monitoring.benchmarker.configurations.artifacts.timeline import (
    TimelineSpecification,
)
from monitoring.benchmarker.reports.report import (
    BenchmarkRunReport,
    BenchmarkScenarioReport,
    StepTerminationReason,
)
from monitoring.monitorlib.fetch import Query
from monitoring.monitorlib.formatting import format_duration_shorthand

DEFAULT_PALETTE = [
    "#32aced",
    "#c7c46b",
    "#70c76b",
    "#c77f6b",
    "#9b59b6",
    "#e67e22",
    "#1abc9c",
    "#e74c3c",
    "#34495e",
    "#16a085",
    "#27ae60",
    "#2980b9",
    "#8e44ad",
    "#2c3e50",
    "#f39c12",
    "#d35400",
]


def natural_sort_key(s: str) -> list[int | str]:
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r"(\d+)", s)
    ]


def _extract_query_summary(query: Query | None) -> dict[str, Any] | None:
    if query is None:
        return None
    summary: dict[str, Any] = {}
    if "query_type" in query and query.query_type:
        summary["query_type"] = query.query_type
    if "participant_id" in query and query.participant_id:
        summary["participant_id"] = query.participant_id
    if "request" in query and query.request:
        req = query.request
        if "method" in req and req.method:
            summary["method"] = req.method
        if "url" in req and req.url:
            summary["url"] = req.url
    if "response" in query and query.response:
        resp = query.response
        if "status_code" in resp and resp.status_code is not None:
            summary["status_code"] = resp.status_code
        if (
            "elapsed_s" in resp
            and resp.elapsed_s is not None
        ):
            summary["elapsed_s"] = resp.elapsed_s
    return summary if summary else None


def _assign_lanes_for_origin(operations: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Assign operations for a single origin into the minimum non-overlapping swim lanes,
    preferentially placing longer-running operations in lanes further to the left.
    """
    if not operations:
        return [[]]

    # Sort by duration descending, tie-break by start time ascending
    operations.sort(key=lambda op: (-op["duration"], op["t0"]))

    lanes: list[list[dict[str, Any]]] = []
    for op in operations:
        placed = False
        for lane in lanes:
            # Check overlap with all operations currently in this lane
            overlap = any(
                max(op["t0"], placed_op["t0"]) < min(op["t1"], placed_op["t1"])
                for placed_op in lane
            )
            if not overlap:
                lane.append(op)
                placed = True
                break
        if not placed:
            lanes.append([op])

    return lanes if lanes else [[]]


def compute_scenario_timeline_data(
    scenario_index: int,
    scenario: BenchmarkScenarioReport,
    spec: TimelineSpecification,
    scenario_name: str | None = None,
) -> dict[str, Any]:
    # Operation specifications & colors
    spec_ops_map = {op_spec.type: op_spec for op_spec in spec.operations}
    color_map: dict[str, str] = {}
    indicator_width_map: dict[str, float] = {}
    for idx, op_spec in enumerate(spec.operations):
        color = (
            op_spec.color
            if "color" in op_spec and op_spec.color
            else DEFAULT_PALETTE[idx % len(DEFAULT_PALETTE)]
        )
        color_map[op_spec.type] = color
        indicator_width_map[op_spec.type] = (
            float(op_spec.success_indicator_width)
            if "success_indicator_width" in op_spec
            and op_spec.success_indicator_width is not None
            else 2.0
        )

    # Extract steps
    steps_data = []
    earliest_step_time = None
    latest_step_time = None
    for step_idx, step in enumerate(scenario.steps):
        t_start = step.start_time.datetime.timestamp()
        t_end = step.end_time.datetime.timestamp()
        t_stab = (
            step.throughput_stability_time.datetime.timestamp()
            if "throughput_stability_time" in step
            and step.throughput_stability_time is not None
            else None
        )

        if earliest_step_time is None or t_start < earliest_step_time:
            earliest_step_time = t_start
        if latest_step_time is None or t_end > latest_step_time:
            latest_step_time = t_end

        term_reason = str(step.termination_reason)
        # Identify symbol
        if term_reason == StepTerminationReason.Completed:
            term_symbol = "✔"
        elif term_reason == StepTerminationReason.StabilityNotAchieved:
            term_symbol = "👎"
        elif term_reason == StepTerminationReason.Unstable:
            term_symbol = "🛑"
        else:
            term_symbol = "✔" if "complete" in term_reason.lower() else "❓"

        steps_data.append(
            {
                "step_index": step_idx,
                "load_factor": step.load_factor,
                "start_time": t_start,
                "throughput_stability_time": t_stab,
                "end_time": t_end,
                "termination_reason": term_reason,
                "termination_symbol": term_symbol,
                "start_time_iso": str(step.start_time),
                "stability_time_iso": str(step.throughput_stability_time)
                if "throughput_stability_time" in step
                and step.throughput_stability_time is not None
                else None,
                "end_time_iso": str(step.end_time),
            }
        )

    # Collect operations of interest per origin
    origin_ops: dict[str, list[dict[str, Any]]] = {}
    earliest_op_time = None
    latest_op_time = None
    total_ops_count = 0
    successful_ops_count = 0
    unsuccessful_ops_count = 0

    for op_group in scenario.operations:
        op_type = op_group.type
        if op_type not in spec_ops_map:
            continue

        color = color_map[op_type]
        indicator_width = indicator_width_map[op_type]

        for orig_group in op_group.origins:
            origin = orig_group.origin
            if origin not in origin_ops:
                origin_ops[origin] = []

            if "outcomes" in orig_group and orig_group.outcomes:
                for outcome in orig_group.outcomes:
                    if "successful" in outcome and outcome.successful:
                        for op in outcome.successful:
                            t0 = op.t0.datetime.timestamp()
                            t1 = op.t1.datetime.timestamp()
                            if earliest_op_time is None or t0 < earliest_op_time:
                                earliest_op_time = t0
                            if latest_op_time is None or t1 > latest_op_time:
                                latest_op_time = t1

                            origin_ops[origin].append(
                                {
                                    "type": op_type,
                                    "t0": t0,
                                    "t1": t1,
                                    "duration": max(0.0, t1 - t0),
                                    "t0_iso": str(op.t0),
                                    "t1_iso": str(op.t1),
                                    "success": True,
                                    "color": color,
                                    "indicator_width": indicator_width,
                                    "query": _extract_query_summary(op.query)
                                    if "query" in op and op.query is not None
                                    else None,
                                }
                            )
                            total_ops_count += 1
                            successful_ops_count += 1

                    if "unsuccessful" in outcome and outcome.unsuccessful:
                        for op in outcome.unsuccessful:
                            t0 = op.t0.datetime.timestamp()
                            t1 = op.t1.datetime.timestamp()
                            if earliest_op_time is None or t0 < earliest_op_time:
                                earliest_op_time = t0
                            if latest_op_time is None or t1 > latest_op_time:
                                latest_op_time = t1

                            origin_ops[origin].append(
                                {
                                    "type": op_type,
                                    "t0": t0,
                                    "t1": t1,
                                    "duration": max(0.0, t1 - t0),
                                    "t0_iso": str(op.t0),
                                    "t1_iso": str(op.t1),
                                    "success": False,
                                    "color": color,
                                    "indicator_width": indicator_width,
                                    "query": _extract_query_summary(op.query)
                                    if "query" in op and op.query is not None
                                    else None,
                                }
                            )
                            total_ops_count += 1
                            unsuccessful_ops_count += 1

    # Determine scenario start and end boundaries
    all_starts = [t for t in (earliest_step_time, earliest_op_time) if t is not None]
    all_ends = [t for t in (latest_step_time, latest_op_time) if t is not None]

    scenario_start = min(all_starts) if all_starts else 0.0
    scenario_end = max(all_ends) if all_ends else scenario_start + 60.0
    if scenario_end <= scenario_start:
        scenario_end = scenario_start + 1.0

    duration = scenario_end - scenario_start
    duration_shorthand = format_duration_shorthand(duration)

    # Sort origins and assign lanes
    sorted_origin_names = sorted(origin_ops.keys(), key=natural_sort_key)
    origins_data = []
    total_operation_lanes = 0

    for orig_name in sorted_origin_names:
        lanes = _assign_lanes_for_origin(origin_ops[orig_name])
        num_lanes = len(lanes)
        total_operation_lanes += num_lanes
        origins_data.append(
            {
                "origin": orig_name,
                "num_lanes": num_lanes,
                "lanes": lanes,
            }
        )

    # Operation types list for legend and UI
    operation_types_data = [
        {
            "type": op_spec.type,
            "name": op_spec.type.split(".")[-1],
            "color": color_map[op_spec.type],
            "indicator_width": indicator_width_map[op_spec.type],
        }
        for op_spec in spec.operations
    ]

    return {
        "scenario_index": scenario_index,
        "scenario_name": scenario_name or f"Scenario {scenario_index}",
        "scenario_start": scenario_start,
        "scenario_end": scenario_end,
        "scenario_duration": duration,
        "duration_shorthand": duration_shorthand,
        "steps": steps_data,
        "origins": origins_data,
        "operation_types": operation_types_data,
        "total_operation_lanes": total_operation_lanes,
        "stats": {
            "total_operations": total_ops_count,
            "successful_operations": successful_ops_count,
            "unsuccessful_operations": unsuccessful_ops_count,
            "total_steps": len(steps_data),
            "total_origins": len(origins_data),
        },
    }


def generate_timeline(
    report: BenchmarkRunReport,
    spec: TimelineSpecification,
    output_dir: str,
) -> None:
    timeline_dir = os.path.join(output_dir, spec.name)
    os.makedirs(timeline_dir, exist_ok=True)
    logger.info(f"Generating timeline artifact in {timeline_dir}")

    scenarios = report.report.scenarios
    config_scenarios = (
        report.configuration.scenarios
        if "configuration" in report
        and report.configuration
        and "scenarios" in report.configuration
        and report.configuration.scenarios
        else []
    )

    scenarios_summary = []
    scenarios_timeline_data = []

    for idx, scenario in enumerate(scenarios):
        scenario_name = (
            config_scenarios[idx].name
            if idx < len(config_scenarios) and "name" in config_scenarios[idx] and config_scenarios[idx].name
            else f"Scenario {idx}"
        )
        timeline_data = compute_scenario_timeline_data(idx, scenario, spec, scenario_name)
        scenarios_timeline_data.append(timeline_data)
        scenarios_summary.append(
            {
                "index": idx,
                "name": scenario_name,
                "filename": f"s{idx}.html",
                "duration": timeline_data["scenario_duration"],
                "duration_shorthand": timeline_data["duration_shorthand"],
                "steps_count": len(timeline_data["steps"]),
                "origins_count": len(timeline_data["origins"]),
                "operations_count": timeline_data["stats"]["total_operations"],
                "successful_operations": timeline_data["stats"]["successful_operations"],
                "unsuccessful_operations": timeline_data["stats"]["unsuccessful_operations"],
                "steps": timeline_data["steps"],
            }
        )

    # Render scenario pages
    scenario_template = jinja_env.get_template("scenario.html")
    for idx, timeline_data in enumerate(scenarios_timeline_data):
        scenario_file = os.path.join(timeline_dir, f"s{idx}.html")
        prev_scenario = f"s{idx - 1}.html" if idx > 0 else None
        next_scenario = f"s{idx + 1}.html" if idx < len(scenarios) - 1 else None

        with open(scenario_file, "w") as f:
            f.write(
                scenario_template.render(
                    scenario_index=idx,
                    scenario_name=timeline_data["scenario_name"],
                    scenario_data_json=json.dumps(timeline_data),
                    timeline_data=timeline_data,
                    spec=spec,
                    report=report,
                    prev_scenario=prev_scenario,
                    next_scenario=next_scenario,
                    total_scenarios=len(scenarios),
                )
            )

    # Render index overview page
    index_template = jinja_env.get_template("index.html")
    index_file = os.path.join(timeline_dir, "index.html")
    with open(index_file, "w") as f:
        f.write(
            index_template.render(
                report=report,
                spec=spec,
                scenarios_summary=scenarios_summary,
            )
        )

    logger.info(
        f"Timeline artifact successfully generated: {index_file} ({len(scenarios)} scenarios)"
    )
