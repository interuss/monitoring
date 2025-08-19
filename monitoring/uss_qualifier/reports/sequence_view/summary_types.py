from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from implicitdict import ImplicitDict

from monitoring.monitorlib.fetch import Query
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.reports.report import (
    ErrorReport,
    FailedCheck,
    PassedCheck,
)
from monitoring.uss_qualifier.resources.definitions import ResourceID
from monitoring.uss_qualifier.scenarios.definitions import TestScenarioTypeName


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
    passed_check: PassedCheck | None = None
    failed_check: FailedCheck | None = None
    query_events: list[Event | str] | None = None
    query: Query | None = None
    note: NoteEvent | None = None

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
    events: list[Event]

    @property
    def rows(self) -> int:
        return len(self.events)


class TestedCase(ImplicitDict):
    name: str
    url: str
    steps: list[TestedStep]

    @property
    def rows(self) -> int:
        return sum(s.rows for s in self.steps)


class EpochType(str, Enum):
    Case = "Case"
    Events = "Events"


class Epoch(ImplicitDict):
    case: TestedCase | None = None
    events: list[Event] | None = None

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
class TestedParticipant:
    has_failures: bool = False
    has_infos: bool = False
    has_successes: bool = False
    has_queries: bool = False


@dataclass
class TestedScenario:
    type: TestScenarioTypeName
    name: str
    url: str
    scenario_index: int
    duration: str
    epochs: list[Epoch]
    participants: dict[ParticipantID, TestedParticipant]
    execution_error: ErrorReport | None
    resource_origins: dict[ResourceID, str]

    @property
    def rows(self) -> int:
        return sum(c.rows for c in self.epochs)


@dataclass
class SkippedAction:
    reason: str


class ActionNodeType(str, Enum):
    Scenario = "Scenario"
    Suite = "Suite"
    ActionGenerator = "ActionGenerator"
    SkippedAction = "SkippedAction"


class ActionNode(ImplicitDict):
    name: str
    node_type: ActionNodeType
    children: list[ActionNode]
    scenario: TestedScenario | None = None
    skipped_action: SkippedAction | None = None

    @property
    def rows(self) -> int:
        return sum(c.rows for c in self.children) if self.children else 1

    @property
    def cols(self) -> int:
        return 1 + max(c.cols for c in self.children) if self.children else 1


@dataclass
class Indexer:
    index: int = 1


@dataclass
class SuiteCell:
    node: ActionNode | None
    first_row: bool
    rowspan: int = 1
    colspan: int = 1


@dataclass
class OverviewRow:
    suite_cells: list[SuiteCell]
    scenario_node: ActionNode | None = None
    skipped_action_node: ActionNode | None = None
    filled: bool = False
