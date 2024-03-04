from __future__ import annotations

import os
from typing import List, Iterator

from implicitdict import ImplicitDict
from loguru import logger

from monitoring.monitorlib.errors import stacktrace_string
from monitoring.monitorlib.versioning import get_code_version
from monitoring.uss_qualifier.action_generators.action_generator import (
    action_generator_type_from_name,
)
from monitoring.uss_qualifier.configurations.configuration import (
    ParticipantID,
    SequenceViewConfiguration,
    TestConfiguration,
)
from monitoring.uss_qualifier.fileio import load_dict_with_references
from monitoring.uss_qualifier.reports import jinja_env
from monitoring.uss_qualifier.reports.report import (
    TestRunReport,
    TestSuiteActionReport,
    Severity,
    SkippedActionReport,
)
from monitoring.uss_qualifier.reports.sequence_view.events import (
    compute_tested_scenario,
)
from monitoring.uss_qualifier.reports.sequence_view.kml import make_scenario_kml
from monitoring.uss_qualifier.reports.sequence_view.summary_types import (
    Indexer,
    ActionNode,
    ActionNodeType,
    SkippedAction,
    OverviewRow,
    SuiteCell,
    EpochType,
    EventType,
)
from monitoring.uss_qualifier.reports.tested_requirements.generate import (
    compute_test_run_information,
)
from monitoring.uss_qualifier.scenarios.documentation.parsing import (
    get_documentation_by_name,
)
from monitoring.uss_qualifier.suites.definitions import ActionType, TestSuiteDefinition


UNATTRIBUTED_PARTICIPANT = "unattributed"


def _skipped_action_of(report: SkippedActionReport) -> ActionNode:
    if report.declaration.get_action_type() == ActionType.TestSuite:
        if (
            "suite_type" in report.declaration.test_suite
            and report.declaration.test_suite.suite_type
        ):
            suite: TestSuiteDefinition = ImplicitDict.parse(
                load_dict_with_references(report.declaration.test_suite.suite_type),
                TestSuiteDefinition,
            )
            parent = ActionNode(
                name=suite.name,
                node_type=ActionNodeType.Suite,
                children=[],
            )
        elif report.declaration.test_suite.suite_definition:
            parent = ActionNode(
                name=report.declaration.test_suite.suite_definition.name,
                node_type=ActionNodeType.Suite,
                children=[],
            )
        else:
            raise ValueError(
                f"Cannot process skipped action for test suite that does not define suite_type nor suite_definition"
            )
        name = "All actions in test suite"
    elif report.declaration.get_action_type() == ActionType.TestScenario:
        docs = get_documentation_by_name(report.declaration.test_scenario.scenario_type)
        return ActionNode(
            name=docs.name,
            node_type=ActionNodeType.SkippedAction,
            children=[],
            skipped_action=SkippedAction(reason=report.reason),
        )
    elif report.declaration.get_action_type() == ActionType.ActionGenerator:
        generator_type = action_generator_type_from_name(
            report.declaration.action_generator.generator_type
        )
        parent = ActionNode(
            name=generator_type.get_name(),
            node_type=ActionNodeType.ActionGenerator,
            children=[],
        )
        name = f"All actions from action generator"
    else:
        raise ValueError(
            f"Cannot process skipped action of type '{report.declaration.get_action_type()}'"
        )
    parent.children.append(
        ActionNode(
            name=name,
            node_type=ActionNodeType.SkippedAction,
            children=[],
            skipped_action=SkippedAction(reason=report.reason),
        )
    )
    return parent


def _compute_action_node(report: TestSuiteActionReport, indexer: Indexer) -> ActionNode:
    (
        is_test_suite,
        is_test_scenario,
        is_action_generator,
    ) = report.get_applicable_report()
    if is_test_scenario:
        return ActionNode(
            name=report.test_scenario.name,
            node_type=ActionNodeType.Scenario,
            children=[],
            scenario=compute_tested_scenario(report.test_scenario, indexer),
        )
    elif is_test_suite:
        children = [_compute_action_node(a, indexer) for a in report.test_suite.actions]
        return ActionNode(
            name=report.test_suite.name,
            node_type=ActionNodeType.Suite,
            children=children,
        )
    elif is_action_generator:
        generator_type = action_generator_type_from_name(
            report.action_generator.generator_type
        )
        return ActionNode(
            name=generator_type.get_name(),
            node_type=ActionNodeType.ActionGenerator,
            children=[
                _compute_action_node(a, indexer)
                for a in report.action_generator.actions
            ],
        )
    else:
        return _skipped_action_of(report.skipped_action)


def _compute_overview_rows(node: ActionNode) -> Iterator[OverviewRow]:
    if node.node_type == ActionNodeType.Scenario:
        yield OverviewRow(suite_cells=[], scenario_node=node)
    elif node.node_type == ActionNodeType.SkippedAction:
        yield OverviewRow(suite_cells=[], skipped_action_node=node)
    else:
        first_row = True
        for child in node.children:
            for row in _compute_overview_rows(child):
                yield OverviewRow(
                    suite_cells=[SuiteCell(node=node, first_row=first_row)]
                    + row.suite_cells,
                    scenario_node=row.scenario_node,
                    skipped_action_node=row.skipped_action_node,
                )
                first_row = False


def _align_overview_rows(rows: List[OverviewRow]) -> None:
    max_suite_cols = max(len(r.suite_cells) for r in rows)
    to_fill = 0
    for row in rows:
        if to_fill > 0:
            row.filled = True
            to_fill -= 1
        elif len(row.suite_cells) < max_suite_cols:
            if row.suite_cells[-1].first_row and all(
                c.node_type == ActionNodeType.Scenario
                for c in row.suite_cells[-1].node.children
            ):
                row.suite_cells[-1].colspan += max_suite_cols - len(row.suite_cells)
                row.filled = True
                to_fill = row.suite_cells[-1].node.rows - 1

    r0 = 0
    while r0 < len(rows):
        if len(rows[r0].suite_cells) < max_suite_cols and not rows[r0].filled:
            r1 = r0 + 1
            while r1 < len(rows):
                if (
                    len(rows[r1].suite_cells) != len(rows[r0].suite_cells)
                    or rows[r1].suite_cells[-1].node != rows[r0].suite_cells[-1].node
                ):
                    break
                r1 += 1
            rows[r0].suite_cells.append(
                SuiteCell(
                    node=None,
                    first_row=True,
                    rowspan=r1 - r0,
                    colspan=max_suite_cols - len(rows[r0].suite_cells),
                )
            )
            rows[r0].filled = True
            r0 = r1
        else:
            r0 += 1


def _enumerate_all_participants(node: ActionNode) -> List[ParticipantID]:
    if node.node_type == ActionNodeType.Scenario:
        return list(node.scenario.participants)
    else:
        result = set()
        for child in node.children:
            for p in _enumerate_all_participants(child):
                result.add(p)
        return list(result)


def _generate_scenario_pages(
    node: ActionNode, config: SequenceViewConfiguration, output_path: str
) -> None:
    if node.node_type == ActionNodeType.Scenario:
        all_participants = list(node.scenario.participants)
        all_participants.sort()
        if UNATTRIBUTED_PARTICIPANT in all_participants:
            all_participants.remove(UNATTRIBUTED_PARTICIPANT)
            all_participants.append(UNATTRIBUTED_PARTICIPANT)
        scenario_file = os.path.join(
            output_path, f"s{node.scenario.scenario_index}.html"
        )
        kml_file = f"./s{node.scenario.scenario_index}.kml"
        template = jinja_env.get_template("sequence_view/scenario.html")
        with open(scenario_file, "w") as f:
            f.write(
                template.render(
                    test_scenario=node.scenario,
                    all_participants=all_participants,
                    kml_file=kml_file if config.render_kml else None,
                    EpochType=EpochType,
                    EventType=EventType,
                    UNATTRIBUTED_PARTICIPANT=UNATTRIBUTED_PARTICIPANT,
                    len=len,
                    str=str,
                    Severity=Severity,
                )
            )
        if config.render_kml:
            try:
                kml_file = os.path.join(
                    output_path, f"s{node.scenario.scenario_index}.kml"
                )
                with open(kml_file, "w") as f:
                    f.write(make_scenario_kml(node.scenario))
            except (ValueError, KeyError, NotImplementedError) as e:
                logger.error(f"Error generating {kml_file}:\n" + stacktrace_string(e))
    else:
        for child in node.children:
            _generate_scenario_pages(child, config, output_path)


def _make_resources_config(config: TestConfiguration) -> dict:
    baseline = {}
    environment = {}
    non_baseline_inputs = (
        config.non_baseline_inputs
        if "non_baseline_inputs" in config and config.non_baseline_inputs
        else []
    )
    for resource_id, resource_dec in config.resources.resource_declarations.items():
        value = {"Specification": resource_dec.specification}
        if "dependencies" in resource_dec and resource_dec.dependencies:
            value["Dependencies"] = {
                f"<code>{local_name}</code>": f"From <code>{source_name}</code> resource"
                for local_name, source_name in resource_dec.dependencies.items()
            }
        key = f"<code>{resource_id}</code> ({resource_dec.resource_type})"
        current_address = "v1.test_run.resources.resource_declarations." + resource_id
        if current_address in non_baseline_inputs:
            environment[key] = value
        else:
            baseline[key] = value
    result = {}
    if baseline:
        result["Baseline"] = baseline
    if environment:
        result["Environment"] = environment
    return result


def generate_sequence_view(
    report: TestRunReport, config: SequenceViewConfiguration, output_path: str
) -> None:
    node = _compute_action_node(report.report, Indexer())

    resources_config = _make_resources_config(report.configuration.v1.test_run)

    os.makedirs(output_path, exist_ok=True)
    _generate_scenario_pages(node, config, output_path)

    overview_rows = list(_compute_overview_rows(node))
    _align_overview_rows(overview_rows)
    max_suite_cols = max(len(r.suite_cells) for r in overview_rows)
    all_participants = _enumerate_all_participants(node)
    all_participants.sort()
    if UNATTRIBUTED_PARTICIPANT in all_participants:
        all_participants.remove(UNATTRIBUTED_PARTICIPANT)
        all_participants.append(UNATTRIBUTED_PARTICIPANT)
    overview_file = os.path.join(output_path, "index.html")
    template = jinja_env.get_template("sequence_view/overview.html")
    with open(overview_file, "w") as f:
        f.write(
            template.render(
                report=report,
                resources_config=resources_config,
                test_run=compute_test_run_information(report),
                overview_rows=overview_rows,
                max_suite_cols=max_suite_cols,
                all_participants=all_participants,
                ActionNodeType=ActionNodeType,
                UNATTRIBUTED_PARTICIPANT=UNATTRIBUTED_PARTICIPANT,
                len=len,
                Severity=Severity,
                codebase_version=get_code_version(),
            )
        )
