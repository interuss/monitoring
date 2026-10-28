from __future__ import annotations

from typing import Any

from monitoring.monitorlib.formatting import format_duration_shorthand
from monitoring.uss_qualifier.reports.report import TestSuiteActionReport
from monitoring.uss_qualifier.reports.sequence_view.events import (
    UNATTRIBUTED_PARTICIPANT,
)
from monitoring.uss_qualifier.reports.sequence_view.summary_types import (
    ActionNode,
    ActionNodeType,
)

ACTION_COLORS = {
    ActionNodeType.Suite: "#32aced",
    ActionNodeType.ActionGenerator: "#c7c46b",
    ActionNodeType.Scenario: "#70c76b",
}


def _assign_columns(actions: list[dict[str, Any]]) -> int:
    """Place each action in the first free column to the right of its parent.

    Allocate in start-time order, with parents first when timestamps match.
    Columns can hold actions at different depths at different times, rather
    than reserving space for a depth's maximum concurrency throughout the run.
    An instantaneous action occupies its timestamp so simultaneous markers
    remain separate. Assignments stay fixed when the timeline is zoomed.
    """
    occupied_until: list[tuple[float, bool]] = []
    for action in sorted(actions, key=lambda a: (a["t0"], a["depth"])):
        parent_index = action["parent_index"]
        column = actions[parent_index]["column"] + 1 if parent_index is not None else 0
        while column < len(occupied_until):
            end, instantaneous = occupied_until[column]
            if end < action["t0"] or (end == action["t0"] and not instantaneous):
                break
            column += 1
        if column == len(occupied_until):
            occupied_until.append((action["t1"], action["t0"] == action["t1"]))
        else:
            occupied_until[column] = (action["t1"], action["t0"] == action["t1"])
        action["column"] = column
    return max(1, len(occupied_until))


def compute_timeline_data(
    report: TestSuiteActionReport, node: ActionNode
) -> dict[str, Any]:
    """Flatten the action tree into time intervals in shared display columns.

    Use the sequence view's existing action tree for scenario indices. For an
    unfinished action, use its last recorded event or child action as its end.
    Omit skipped actions, and place children to the right of their parents.
    """
    actions: list[dict[str, Any]] = []

    def visit(
        action: TestSuiteActionReport,
        action_node: ActionNode,
        depth: int,
        parent_index: int | None = None,
    ) -> dict[str, Any] | None:
        if action.skipped_action:
            return None
        node_type = action_node.node_type
        start = action.start_time
        assert start is not None
        t0 = start.datetime.timestamp()
        end = action.end_time
        item = {
            "name": action_node.name,
            "type": node_type.value,
            "depth": depth,
            "parent_index": parent_index,
            "t0": t0,
            "color": ACTION_COLORS[node_type],
            "href": None,
            "participants": [],
            "participant_checks": [],
            "passed_checks": 0,
            "failed_checks": 0,
            "query_count": 0,
            "execution_error": None,
            "end_inferred": end is None,
        }
        item_index = len(actions)
        actions.append(item)
        children = []
        if action.test_suite or action.action_generator:
            parent = action.test_suite or action.action_generator
            assert parent is not None
            if action.test_suite:
                item["class_name"] = action.test_suite.suite_type
            else:
                assert action.action_generator is not None
                item["class_name"] = action.action_generator.generator_type
            for child, child_node in zip(
                parent.actions, action_node.children, strict=True
            ):
                child_item = visit(child, child_node, depth + 1, item_index)
                if child_item is not None:
                    children.append(child_item)
        if action.test_scenario:
            scenario = action.test_scenario
            assert action_node.scenario is not None
            item["href"] = f"s{action_node.scenario.scenario_index}.html"
            item["scenario_index"] = action_node.scenario.scenario_index
            item["class_name"] = scenario.scenario_type
            item["participants"] = sorted(action_node.scenario.participants)
            passed_checks = [check for _, check in scenario.query_passed_checks()]
            failed_checks = [check for _, check in scenario.query_failed_checks()]
            item["passed_checks"] = len(passed_checks)
            item["failed_checks"] = len(failed_checks)
            item["query_count"] = len(scenario.queries())
            checked_participants = {
                p
                for check in passed_checks + failed_checks
                for p in (check.participants or [UNATTRIBUTED_PARTICIPANT])
            }
            failed_participants = {
                p
                for check in failed_checks
                for p in (check.participants or [UNATTRIBUTED_PARTICIPANT])
            }
            item["participant_checks"] = [
                {"id": p, "has_failed_checks": p in failed_participants}
                for p in sorted(checked_participants)
            ]
            if scenario.execution_error:
                item["execution_error"] = scenario.execution_error.message
            latest = scenario.latest_timestamp
            if end is None and latest is not None:
                t1 = latest.timestamp()
            else:
                t1 = end.datetime.timestamp() if end else t0
        else:
            t1 = (
                end.datetime.timestamp()
                if end
                else max((child["t1"] for child in children), default=t0)
            )
            item["participants"] = sorted(
                {p for child in children for p in child["participants"]}
            )
            item["passed_checks"] = sum(c["passed_checks"] for c in children)
            item["failed_checks"] = sum(c["failed_checks"] for c in children)
            item["query_count"] = sum(c["query_count"] for c in children)
        item["t1"] = max(t0, t1)
        item["duration"] = item["t1"] - t0
        return item

    visit(report, node, 0)
    fallback_start = report.start_time
    start = min(
        (a["t0"] for a in actions),
        default=fallback_start.datetime.timestamp() if fallback_start else 0,
    )
    end = max((a["t1"] for a in actions), default=start)
    columns = _assign_columns(actions)
    return {
        "scenario_start": start,
        "scenario_end": end if end > start else start + 1,
        "duration_shorthand": format_duration_shorthand(end - start),
        "columns": columns,
        "actions": actions,
        "action_types": [
            {"name": t.value, "color": color} for t, color in ACTION_COLORS.items()
        ],
        "scenario_count": sum(a["type"] == ActionNodeType.Scenario for a in actions),
    }
