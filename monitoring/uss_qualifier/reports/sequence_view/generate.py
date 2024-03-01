from __future__ import annotations

import math
import os
import html
from datetime import datetime
from typing import List, Dict, Iterator, Tuple, Optional

from implicitdict import ImplicitDict
from loguru import logger

from monitoring.monitorlib.errors import stacktrace_string
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
    TestScenarioReport,
    Severity,
    SkippedActionReport,
    TestStepReport,
)
from monitoring.uss_qualifier.reports.sequence_view.kml import make_scenario_kml
from monitoring.uss_qualifier.reports.sequence_view.summary_types import (
    TestedScenario,
    Indexer,
    Event,
    NoteEvent,
    Epoch,
    TestedParticipant,
    ActionNode,
    ActionNodeType,
    SkippedAction,
    OverviewRow,
    SuiteCell,
    EpochType,
    EventType,
    TestedStep,
    TestedCase,
)
from monitoring.uss_qualifier.reports.tested_requirements.generate import (
    compute_test_run_information,
)
from monitoring.uss_qualifier.scenarios.documentation.parsing import (
    get_documentation_by_name,
)
from monitoring.uss_qualifier.suites.definitions import ActionType, TestSuiteDefinition


UNATTRIBUTED_PARTICIPANT = "unattributed"


def _note_events(
    note_parent: ImplicitDict,
    indexer: Indexer,
    after: Optional[datetime] = None,
    before: Optional[datetime] = None,
) -> List[Event]:
    if "notes" not in note_parent or not note_parent.notes:
        return []
    events = []
    for k, v in note_parent.notes.items():
        if after is not None and v.timestamp.datetime < after:
            continue
        if before is not None and v.timestamp.datetime > before:
            continue
        events.append(
            Event(
                note=NoteEvent(
                    key=html.escape(k),
                    message=html.escape(v.message),
                    timestamp=v.timestamp.datetime,
                ),
                event_index=0,
            )
        )
    if not events:
        return []
    events.sort(key=lambda e: e.timestamp)
    for e in events:
        e.event_index = indexer.index
        indexer.index += 1
    return events


def _step_events(
    step: TestStepReport,
    note_parent: ImplicitDict,
    indexer: Indexer,
    scenario_participants: Dict[ParticipantID, TestedParticipant],
    all_events: List[Event],
    after: Optional[datetime],
) -> Tuple[TestedStep, datetime]:
    events = []

    # Create events for this step's passed checks
    for passed_check in step.passed_checks:
        # Create the new event and update event lists
        events.append(Event(passed_check=passed_check))
        all_events.append(events[-1])

        # Update tested participants
        participants = (
            passed_check.participants
            if passed_check.participants
            else [UNATTRIBUTED_PARTICIPANT]
        )
        for pid in participants:
            p = scenario_participants.get(pid, TestedParticipant())
            p.has_successes = True
            scenario_participants[pid] = p

    # Create events for this step's queries
    if "queries" in step and step.queries:
        for query in step.queries:
            # Create the new event and update event lists
            events.append(Event(query=query))
            all_events.append(events[-1])

            # Update tested participants
            participant_id = (
                query.participant_id
                if "participant_id" in query and query.participant_id
                else UNATTRIBUTED_PARTICIPANT
            )
            p = scenario_participants.get(participant_id, TestedParticipant())
            p.has_queries = True
            scenario_participants[participant_id] = p

    # Create events for this step's failed checks
    for failed_check in step.failed_checks:
        # Find the query events related to this failed check
        query_events = []
        if (
            "query_report_timestamps" in failed_check
            and failed_check.query_report_timestamps
        ):
            for query_timestamp in failed_check.query_report_timestamps:
                found = False
                for e in all_events:
                    if (
                        e.type == EventType.Query
                        and e.query.request.initiated_at == query_timestamp
                    ):
                        query_events.append(e)
                        found = True
                        break
                if not found:
                    query_events.append(query_timestamp)

        # Create the new event and update event lists
        e = Event(failed_check=failed_check, query_events=query_events)
        events.append(e)
        all_events.append(e)

        # Update tested participants
        participants = (
            failed_check.participants
            if failed_check.participants
            else [UNATTRIBUTED_PARTICIPANT]
        )
        for pid in participants:
            p = scenario_participants.get(pid, TestedParticipant())
            if failed_check.severity == Severity.Low:
                p.has_infos = True
            else:
                p.has_failures = True
            scenario_participants[pid] = p

    # Look for the latest time something happened for this step
    latest_step_time = None
    for e in events:
        if latest_step_time is None or e.timestamp > latest_step_time:
            latest_step_time = e.timestamp
    if "end_time" in step and step.end_time:
        if latest_step_time is None or step.end_time.datetime > latest_step_time:
            latest_step_time = step.end_time.datetime

    # Include any events that occurred after the last step and before the end of this step as part of this step
    events.extend(_note_events(note_parent, indexer, after, latest_step_time))

    # Sort this step's events by time
    events.sort(key=lambda e: e.timestamp)

    # Label this step's events with indexer
    for e in events:
        e.event_index = indexer.index
        indexer.index += 1

    # Build and return this step
    return (
        TestedStep(
            name=step.name,
            url=step.documentation_url,
            events=events,
        ),
        latest_step_time,
    )


def _compute_tested_scenario(
    report: TestScenarioReport, action_indexer: Indexer
) -> TestedScenario:
    epochs = []
    all_events = []
    indexer = Indexer(index=1)
    scenario_participants: Dict[ParticipantID, TestedParticipant] = {}

    # Add any notes that occurred before the first test step
    latest_step_time = (
        report.cases[0].steps[0].start_time.datetime
        if report.cases and report.cases[0].steps
        else None
    )
    pre_notes = _note_events(report, indexer, before=latest_step_time)
    if pre_notes:
        epochs.append(Epoch(events=pre_notes))
        all_events.extend(pre_notes)

    # Add all cases
    for case in report.cases:
        steps = []
        for step in case.steps:
            tested_step, latest_step_time = _step_events(
                step,
                report,
                indexer,
                scenario_participants,
                all_events,
                latest_step_time,
            )
            steps.append(tested_step)
        tested_case = TestedCase(
            name=case.name, url=case.documentation_url, steps=steps
        )
        epochs.append(Epoch(case=tested_case))

    # Add cleanup
    if "cleanup" in report and report.cleanup:
        # Attach any notes prior to cleanup start time to most recent step
        dangling_notes = _note_events(
            report,
            indexer,
            before=report.cleanup.start_time.datetime,
            after=latest_step_time,
        )
        epochs[-1].case.steps[-1].events.extend(dangling_notes)

        # Add a one-step case for cleanup
        tested_step, latest_step_time = _step_events(
            report.cleanup,
            report,
            indexer,
            scenario_participants,
            all_events,
            report.cleanup.start_time.datetime,
        )
        epochs.append(Epoch(case=TestedCase(name="", url="#", steps=[tested_step])))

    # Add any notes that occurred after the last included time
    post_notes = _note_events(report, indexer, after=latest_step_time)
    if post_notes:
        epochs.append(Epoch(events=post_notes))
        all_events.extend(post_notes)

    if (
        "end_time" in report
        and report.end_time
        and report.end_time.datetime > latest_step_time
    ):
        latest_step_time = report.end_time.datetime

    if latest_step_time is not None:
        dt_s = round((latest_step_time - report.start_time.datetime).total_seconds())
    else:
        dt_s = 0
    dt_m = math.floor(dt_s / 60)
    dt_s -= dt_m * 60
    padding = "0" if dt_s < 10 else ""
    duration = f"{dt_m}:{padding}{dt_s}"

    scenario = TestedScenario(
        type=report.scenario_type,
        name=report.name,
        url=report.documentation_url,
        duration=duration,
        epochs=epochs,
        scenario_index=action_indexer.index,
        participants=scenario_participants,
        execution_error=report.execution_error if "execution_error" in report else None,
    )
    action_indexer.index += 1
    return scenario


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
            scenario=_compute_tested_scenario(report.test_scenario, indexer),
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
            )
        )
