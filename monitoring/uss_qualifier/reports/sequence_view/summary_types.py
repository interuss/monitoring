from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union

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
    has_failures: bool = False
    has_infos: bool = False
    has_successes: bool = False
    has_queries: bool = False


@dataclass
class TestedScenario(object):
    type: TestScenarioTypeName
    name: str
    url: str
    scenario_index: int
    duration: str
    epochs: List[Epoch]
    participants: Dict[ParticipantID, TestedParticipant]
    execution_error: Optional[ErrorReport]
    resource_origins: Dict[ResourceID, str]

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
    index: int = 1


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
