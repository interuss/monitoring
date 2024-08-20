from __future__ import annotations

import math
import html
from datetime import datetime
from typing import List, Dict, Tuple, Optional

from implicitdict import ImplicitDict

from monitoring.uss_qualifier.configurations.configuration import (
    ParticipantID,
)
from monitoring.uss_qualifier.reports.report import (
    TestScenarioReport,
    Severity,
    TestStepReport,
)
from monitoring.uss_qualifier.reports.sequence_view.summary_types import (
    TestedScenario,
    Indexer,
    Event,
    NoteEvent,
    Epoch,
    TestedParticipant,
    EventType,
    TestedStep,
    TestedCase,
)


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


def compute_tested_scenario(
    report: TestScenarioReport, action_indexer: Indexer
) -> TestedScenario:
    """Compute the event information needed for showing a sequence view of the specified scenario.

    Args:
        report: Report of test scenario to extract events from.
        action_indexer: Indexer of displayed test scenarios.

    Returns: Test scenario results summarized for sequence view display.
    """
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
        if dangling_notes:
            if not epochs:
                # Nothing happened during this scenario, so add a virtual test case
                epochs.append(
                    Epoch(case=TestedCase(name="No actions", url="#", steps=[]))
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
        and (latest_step_time is None or report.end_time.datetime > latest_step_time)
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
