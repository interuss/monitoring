from __future__ import annotations
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import html
from typing import List, Dict, Optional, Iterator, Union

from implicitdict import ImplicitDict

from monitoring.monitorlib.fetch import Query
from monitoring.uss_qualifier.configurations.configuration import (
    ParticipantID,
    SequenceViewConfiguration,
    TestConfiguration,
)
from monitoring.uss_qualifier.fileio import load_content, load_dict_with_references
from monitoring.uss_qualifier.reports import jinja_env
from monitoring.uss_qualifier.reports.report import (
    TestRunReport,
    TestSuiteActionReport,
    TestScenarioReport,
    PassedCheck,
    FailedCheck,
    SkippedActionReport,
)
from monitoring.uss_qualifier.reports.tested_requirements import (
    compute_test_run_information,
)
from monitoring.uss_qualifier.scenarios.definitions import TestScenarioTypeName
from monitoring.uss_qualifier.scenarios.documentation.parsing import (
    get_documentation_by_name,
)
from monitoring.uss_qualifier.suites.definitions import ActionType, TestSuiteDefinition


class NoteEvent(ImplicitDict):
    key: str
    message: str
    timestamp: datetime


class EventType(str, Enum):
    PassedCheck = "PassedCheck"
    FailedCheck = "FailedCheck"
    Query = "Query"
    Note = "Note"


class Event(ImplicitDict):
    event_index: int = 0
    passed_check: Optional[PassedCheck] = None
    failed_check: Optional[FailedCheck] = None
    query_events: Optional[List[Union[Event, str]]] = None
    query: Optional[Query] = None
    note: Optional[NoteEvent] = None

    @property
    def type(self) -> EventType:
        if self.passed_check:
            return EventType.PassedCheck
        elif self.failed_check:
            return EventType.FailedCheck
        elif self.query:
            return EventType.Query
        elif self.note:
            return EventType.Note
        else:
            raise ValueError("Invalid Event type")

    @property
    def timestamp(self) -> datetime:
        if self.passed_check:
            return self.passed_check.timestamp.datetime
        elif self.failed_check:
            return self.failed_check.timestamp.datetime
        elif self.query:
            return self.query.request.timestamp
        elif self.note:
            return self.note.timestamp
        else:
            raise ValueError("Invalid Event type")

    def get_query_links(self) -> str:
        links = []
        for e in self.query_events:
            if isinstance(e, str):
                links.append(e)
            else:
                links.append(f'<a href="#e{e.event_index}">{e.event_index}</a>')
        return ", ".join(links)


class TestedStep(ImplicitDict):
    name: str
    url: str
    events: List[Event]

    @property
    def rows(self) -> int:
        return len(self.events)


class TestedCase(ImplicitDict):
    name: str
    url: str
    steps: List[TestedStep]

    @property
    def rows(self) -> int:
        return sum(s.rows for s in self.steps)


class EpochType(str, Enum):
    Case = "Case"
    Events = "Events"


class Epoch(ImplicitDict):
    case: Optional[TestedCase] = None
    events: Optional[List[Event]] = None

    @property
    def type(self) -> EpochType:
        if self.case:
            return EpochType.Case
        elif self.events:
            return EpochType.Events
        else:
            raise ValueError("Invalid Epoch did not specify case or events")

    @property
    def rows(self) -> int:
        if self.case:
            return self.case.rows
        elif self.events:
            return len(self.events)
        else:
            raise ValueError("Invalid Epoch did not specify case or events")


@dataclass
class TestedParticipant(object):
    has_failures: bool


class TestedScenario(ImplicitDict):
    type: TestScenarioTypeName
    name: str
    url: str
    scenario_index: int
    epochs: List[Epoch]
    participants: Dict[ParticipantID, TestedParticipant]

    @property
    def rows(self) -> int:
        return sum(c.rows for c in self.epochs)


@dataclass
class SkippedAction(object):
    reason: str


class ActionNodeType(str, Enum):
    Scenario = "Scenario"
    Suite = "Suite"
    ActionGenerator = "ActionGenerator"
    SkippedAction = "SkippedAction"


class ActionNode(ImplicitDict):
    name: str
    node_type: ActionNodeType
    children: List[ActionNode]
    scenario: Optional[TestedScenario] = None
    skipped_action: Optional[SkippedAction] = None

    @property
    def rows(self) -> int:
        return sum(c.rows for c in self.children) if self.children else 1

    @property
    def cols(self) -> int:
        return 1 + max(c.cols for c in self.children) if self.children else 1


@dataclass
class Indexer(object):
    scenario_index: int = 1


@dataclass
class SuiteCell(object):
    node: Optional[ActionNode]
    first_row: bool
    rowspan: int = 1
    colspan: int = 1


@dataclass
class OverviewRow(object):
    suite_cells: List[SuiteCell]
    scenario_node: Optional[ActionNode] = None
    skipped_action_node: Optional[ActionNode] = None
    filled: bool = False


def _compute_tested_scenario(
    report: TestScenarioReport, indexer: Indexer
) -> TestedScenario:
    epochs = []
    all_events = []
    event_index = 1

    def append_notes(new_notes):
        nonlocal event_index, all_events
        events = []
        for k, v in new_notes.items():
            events.append(
                Event(
                    note=NoteEvent(
                        key=html.escape(k),
                        message=html.escape(v.message),
                        timestamp=v.timestamp.datetime,
                    ),
                    event_index=event_index,
                )
            )
            all_events.append(events[-1])
            event_index += 1
        events.sort(key=lambda e: e.timestamp)
        epochs.append(Epoch(events=events))

    # Add any notes that occurred before the first test step
    if "notes" in report and report.notes:
        if len(report.cases) >= 1 and len(report.cases[0].steps) >= 1:
            first_step_start = report.cases[0].steps[0].start_time.datetime
            pre_notes = {
                k: v
                for k, v in report.notes.items()
                if v.timestamp.datetime < first_step_start
            }
        else:
            pre_notes = report.notes
        if pre_notes:
            append_notes(pre_notes)

    scenario_participants: Dict[ParticipantID, TestedParticipant] = {}

    latest_step_time = None
    for case in report.cases:
        steps = []
        last_step = None
        for step in case.steps:
            if "notes" in report and report.notes:
                # Add events (notes) that happened in between the previous step and this one
                if last_step is not None:
                    inter_notes = {
                        k: v
                        for k, v in report.notes.items()
                        if last_step.end_time.datetime
                        < v.timestamp.datetime
                        < step.start_time.datetime
                    }
                    if inter_notes:
                        append_notes(inter_notes)
                else:
                    last_step = step

            # Enumerate the events of this step
            events = []
            for passed_check in step.passed_checks:
                events.append(Event(passed_check=passed_check))
                all_events.append(events[-1])
                for pid in passed_check.participants:
                    p = scenario_participants.get(
                        pid, TestedParticipant(has_failures=False)
                    )
                    scenario_participants[pid] = p
            if "queries" in step and step.queries:
                for query in step.queries:
                    events.append(Event(query=query))
                    all_events.append(events[-1])
                    if "server_id" in query and query.server_id:
                        p = scenario_participants.get(
                            query.server_id, TestedParticipant(has_failures=False)
                        )
                        scenario_participants[query.server_id] = p
            for failed_check in step.failed_checks:
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
                events.append(
                    Event(failed_check=failed_check, query_events=query_events)
                )
                all_events.append(events[-1])
                for pid in failed_check.participants:
                    p = scenario_participants.get(
                        pid, TestedParticipant(has_failures=True)
                    )
                    p.has_failures = True
                    scenario_participants[pid] = p
            if "notes" in report and report.notes:
                for key, note in report.notes.items():
                    if step.start_time.datetime <= note.timestamp.datetime:
                        if (
                            "end_time" not in step
                            or note.timestamp.datetime <= step.end_time.datetime
                        ):
                            events.append(
                                Event(
                                    note=NoteEvent(
                                        key=html.escape(key),
                                        message=html.escape(note.message),
                                        timestamp=note.timestamp.datetime,
                                    )
                                )
                            )
                            all_events.append(events[-1])

            # Sort this step's events by time
            events.sort(key=lambda e: e.timestamp)

            # Label this step's events with event_index
            for e in events:
                e.event_index = event_index
                event_index += 1

            # Look for the latest time something happened
            for e in events:
                if latest_step_time is None or e.timestamp > latest_step_time:
                    latest_step_time = e.timestamp
            if "end_time" in step and step.end_time:
                if (
                    latest_step_time is None
                    or step.end_time.datetime > latest_step_time
                ):
                    latest_step_time = step.end_time.datetime

            # Add this step
            steps.append(
                TestedStep(
                    name=step.name,
                    url=step.documentation_url,
                    events=events,
                )
            )
        epochs.append(
            Epoch(
                case=TestedCase(name=case.name, url=case.documentation_url, steps=steps)
            )
        )

    # Add any notes that occurred after the last test step
    if "notes" in report and report.notes:
        if len(report.cases) >= 1 and len(report.cases[0].steps) >= 1:
            post_notes = {
                k: v
                for k, v in report.notes.items()
                if v.timestamp.datetime > latest_step_time
            }
        else:
            post_notes = {}
        if post_notes:
            append_notes(post_notes)

    scenario = TestedScenario(
        type=report.scenario_type,
        name=report.name,
        url=report.documentation_url,
        epochs=epochs,
        scenario_index=indexer.scenario_index,
        participants=scenario_participants,
    )
    indexer.scenario_index += 1
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
        name = "All scenarios in test suite"
    elif report.declaration.get_action_type() == ActionType.TestScenario:
        docs = get_documentation_by_name(report.declaration.test_scenario.scenario_type)
        return ActionNode(
            name=docs.name,
            node_type=ActionNodeType.SkippedAction,
            children=[],
            skipped_action=SkippedAction(reason=report.reason),
        )
    elif report.declaration.get_action_type() == ActionType.ActionGenerator:
        parent = ActionNode(
            name=report.declaration.action_generator.generator_type,
            node_type=ActionNodeType.ActionGenerator,
            children=[],
        )
        name = f"All scenarios from action generator"
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
        for skipped_action in report.test_suite.skipped_actions:
            i = 0
            for i, a in enumerate(report.test_suite.actions):
                if a.start_time.datetime > skipped_action.timestamp.datetime:
                    break
            children.insert(i, _skipped_action_of(skipped_action))
        return ActionNode(
            name=report.test_suite.name,
            node_type=ActionNodeType.Suite,
            children=children,
        )
    elif is_action_generator:
        return ActionNode(
            name=report.action_generator.generator_type,
            node_type=ActionNodeType.ActionGenerator,
            children=[
                _compute_action_node(a, indexer)
                for a in report.action_generator.actions
            ],
        )
    else:
        raise ValueError(
            "Invalid TestSuiteActionReport; doesn't specify scenario, suite, or action generator"
        )


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
    node: ActionNode, config: SequenceViewConfiguration
) -> None:
    if node.node_type == ActionNodeType.Scenario:
        all_participants = list(node.scenario.participants)
        all_participants.sort()
        scenario_file = os.path.join(
            config.output_path, f"s{node.scenario.scenario_index}.html"
        )
        template = jinja_env.get_template("sequence_view/scenario.html")
        with open(scenario_file, "w") as f:
            f.write(
                template.render(
                    test_scenario=node.scenario,
                    all_participants=all_participants,
                    EpochType=EpochType,
                    EventType=EventType,
                    len=len,
                    str=str,
                )
            )
    else:
        for child in node.children:
            _generate_scenario_pages(child, config)


def generate_sequence_view(
    report: TestRunReport, config: SequenceViewConfiguration
) -> None:
    node = _compute_action_node(report.report, Indexer())

    os.makedirs(config.output_path, exist_ok=True)
    _generate_scenario_pages(node, config)

    overview_rows = list(_compute_overview_rows(node))
    _align_overview_rows(overview_rows)
    max_suite_cols = max(len(r.suite_cells) for r in overview_rows)
    all_participants = _enumerate_all_participants(node)
    all_participants.sort()
    overview_file = os.path.join(config.output_path, "index.html")
    template = jinja_env.get_template("sequence_view/overview.html")
    with open(overview_file, "w") as f:
        f.write(
            template.render(
                report=report,
                test_run=compute_test_run_information(report),
                overview_rows=overview_rows,
                max_suite_cols=max_suite_cols,
                all_participants=all_participants,
                ActionNodeType=ActionNodeType,
                len=len,
            )
        )
