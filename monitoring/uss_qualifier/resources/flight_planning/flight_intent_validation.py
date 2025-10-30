from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta

import arrow
from implicitdict import StringBasedTimeDelta

from monitoring.monitorlib.clients.flight_planning.flight_info import (
    AirspaceUsageState,
    FlightInfo,
    UasState,
)
from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    FlightInfoTemplate,
)
from monitoring.monitorlib.geotemporal import Volume4D, Volume4DCollection
from monitoring.monitorlib.temporal import TestTimeContext, Time, TimeDuringTest
from monitoring.monitorlib.uspace import problems_with_flight_authorisation
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntentID,
)

FlightIntentName = str

MAX_TEST_RUN_DURATION = timedelta(minutes=45)
"""The longest a test run might take (to estimate flight intent timestamps prior to scenario execution)"""


@dataclass
class ExpectedFlightIntent:
    intent_id: FlightIntentID
    name: FlightIntentName
    must_conflict_with: list[FlightIntentName] | None = None
    must_not_conflict_with: list[FlightIntentName] | None = None
    usage_state: AirspaceUsageState | None = None
    uas_state: UasState | None = None
    f3548v21_priority_higher_than: list[FlightIntentName] | None = None
    f3548v21_priority_equal_to: list[FlightIntentName] | None = None
    earliest_time_start: StringBasedTimeDelta | None = None
    latest_time_start: StringBasedTimeDelta | None = None
    earliest_time_end: StringBasedTimeDelta | None = None
    latest_time_end: StringBasedTimeDelta | None = None
    valid_uspace_flight_auth: bool | None = None


def validate_flight_intent_templates(
    templates: dict[FlightIntentID, FlightInfoTemplate],
    expected_intents: list[ExpectedFlightIntent],
) -> Volume4D:
    """
    Returns: the bounding extents of the flight intent templates
    """
    extents = Volume4DCollection([])

    now = Time(arrow.utcnow().datetime)
    context = TestTimeContext.all_times_are(now)
    flight_intents = {k: v.resolve(context) for k, v in templates.items()}
    for flight_intent in flight_intents.values():
        extents.extend(flight_intent.basic_information.area)
    validate_flight_intents(flight_intents, expected_intents, now)

    later = Time(now.datetime + MAX_TEST_RUN_DURATION)
    context = TestTimeContext.all_times_are(later)
    context[TimeDuringTest.StartOfTestRun] = now
    flight_intents = {k: v.resolve(context) for k, v in templates.items()}
    for flight_intent in flight_intents.values():
        extents.extend(flight_intent.basic_information.area)
    validate_flight_intents(flight_intents, expected_intents, later)

    return extents.bounding_volume


def validate_flight_intents(
    intents: dict[FlightIntentID, FlightInfo],
    expected_intents: list[ExpectedFlightIntent],
    now: Time,
) -> None:
    """Validate that `intents` contains all intents meeting all the criteria in `expected_intents`.

    Args:
        intents: Flight intents we actually have.
        expected_intents: Criteria that our flight intents are expected to meet.
        now: Current time, for validation that in-use intents include this time.

    Raises:
        * ValueError when a validation criterion is not met.
    """

    # Ensure all intents are present
    for expected_intent in expected_intents:
        if expected_intent.intent_id not in intents:
            raise ValueError(f"Missing flight intent `{expected_intent.intent_id}`")

    for expected_intent in expected_intents:
        intent = intents[expected_intent.intent_id]

        # Ensure in-use intent includes now
        if intent.basic_information.usage_state == AirspaceUsageState.InUse:
            start_time = intent.basic_information.area.time_start
            if start_time is None:
                raise ValueError(
                    f"At least one volume in `{expected_intent.intent_id}` is missing a start time"
                )
            if now.datetime < start_time.datetime:
                raise ValueError(
                    f"When evaluated at {now.datetime.isoformat()}, `{expected_intent.intent_id}`'s start time {start_time.datetime.isoformat()} is in the future even though the intent is indicated as InUse"
                )
            end_time = intent.basic_information.area.time_end
            if end_time is None:
                raise ValueError(
                    f"At least one volume in `{expected_intent.intent_id}` is missing an end time"
                )
            if now.datetime > end_time.datetime:
                raise ValueError(
                    f"When evaluated at {now.datetime.isoformat()}, `{expected_intent.intent_id}`'s end time {end_time.datetime.isoformat()} is in the past even though the intent is indicated as InUse"
                )

        # Ensure not-in-use intent does not indicate an off-nominal UAS
        if intent.basic_information.usage_state != AirspaceUsageState.InUse:
            if intent.basic_information.uas_state != UasState.Nominal:
                raise ValueError(
                    f"`{expected_intent.intent_id}` indicates the intent is not in use ({intent.basic_information.usage_state}), but the UAS state is specified as off-nominal ({intent.basic_information.uas_state})"
                )

        def named_intents(
            name: FlightIntentName,
            exclude: ExpectedFlightIntent,
            no_matches_message: str,
        ) -> Iterator[ExpectedFlightIntent]:
            found = False
            for expected_intent in expected_intents:
                if expected_intent is exclude:
                    continue
                if expected_intent.name != name:
                    continue
                found = True
                yield expected_intent
            if not found:
                raise ValueError(no_matches_message)

        # Ensure conflicts with other intents
        if expected_intent.must_conflict_with:
            for conflict_name in expected_intent.must_conflict_with:
                msg = f"Invalid flight intent expectation: `{expected_intent.intent_id}` must conflict with intent name `{conflict_name}` but there are no expected flight intents with that name"
                for other_expected_intent in named_intents(
                    conflict_name, expected_intent, msg
                ):
                    other_intent = intents[other_expected_intent.intent_id]
                    if not intent.basic_information.area.intersects_vol4s(
                        other_intent.basic_information.area
                    ):
                        raise ValueError(
                            f"Flight intent `{expected_intent.intent_id}` must conflict with intent name `{conflict_name}` but there are no conflicts with `{other_expected_intent.intent_id}`"
                        )

        # Ensure free of conflicts with other intents
        if expected_intent.must_not_conflict_with:
            for conflict_name in expected_intent.must_not_conflict_with:
                msg = f"Invalid flight intent expectation: `{expected_intent.intent_id}` must not conflict with intent name `{conflict_name}` but there are no expected flight intents with that name"
                for other_expected_intent in named_intents(
                    conflict_name, expected_intent, msg
                ):
                    other_intent = intents[other_expected_intent.intent_id]
                    if intent.basic_information.area.intersects_vol4s(
                        other_intent.basic_information.area
                    ):
                        raise ValueError(
                            f"Flight intent `{expected_intent.intent_id}` must not conflict with intent name `{conflict_name}` but there is a conflict with `{other_expected_intent.intent_id}`"
                        )

        # Ensure usage state
        if expected_intent.usage_state:
            if intent.basic_information.usage_state != expected_intent.usage_state:
                raise ValueError(
                    f"Flight intent `{expected_intent.intent_id}` must have usage_state {expected_intent.usage_state}, but instead has usage_state {intent.basic_information.usage_state}"
                )

        # Ensure UAS state
        if expected_intent.uas_state:
            if intent.basic_information.uas_state != expected_intent.uas_state:
                raise ValueError(
                    f"Flight intent `{expected_intent.intent_id}` must have uas_state {expected_intent.uas_state}, but instead has uas_state {intent.basic_information.uas_state}"
                )

        # Ensure ASTM F3548-21 priority higher than other intents
        if expected_intent.f3548v21_priority_higher_than:
            for priority_name in expected_intent.f3548v21_priority_higher_than:
                msg = f"Invalid flight intent expectation: `{expected_intent.intent_id}` must be higher ASTM F3548-21 priority than intent `{priority_name}` but there are no expected flight intents with that name"
                for other_expected_intent in named_intents(
                    priority_name, expected_intent, msg
                ):
                    other_intent = intents[other_expected_intent.intent_id]
                    if (
                        intent.astm_f3548_21.priority
                        <= other_intent.astm_f3548_21.priority
                    ):
                        raise ValueError(
                            f"Flight intent `{expected_intent.intent_id}` with ASTM F3548-21 priority {intent.astm_f3548_21.priority} must be higher priority than intent name `{priority_name}` but `{other_expected_intent.intent_id}` has priority {other_intent.astm_f3548_21.priority}"
                        )

        # Ensure ASTM F3548-21 priority equal to other intents
        if expected_intent.f3548v21_priority_equal_to:
            for priority_name in expected_intent.f3548v21_priority_equal_to:
                msg = f"Invalid flight intent expectation: `{expected_intent.intent_id}` must be equal ASTM F3548-21 priority to intent `{priority_name}` but there are no expected flight intents with that name"
                for other_expected_intent in named_intents(
                    priority_name, expected_intent, msg
                ):
                    other_intent = intents[other_expected_intent.intent_id]
                    if (
                        intent.astm_f3548_21.priority
                        != other_intent.astm_f3548_21.priority
                    ):
                        raise ValueError(
                            f"Flight intent `{expected_intent.intent_id}` with ASTM F3548-21 priority {intent.astm_f3548_21.priority} must be equal priority to intent name `{priority_name}` but `{other_expected_intent.intent_id}` has priority {other_intent.astm_f3548_21.priority}"
                        )

        # Ensure start/end times within required bounds
        if (
            expected_intent.earliest_time_start or expected_intent.latest_time_start
        ) and not intent.basic_information.area.time_start:
            raise ValueError(
                f"Flight intent `{expected_intent.intent_id}` has a time_start bound requirement but has no time_start specified"
            )
        if (
            expected_intent.earliest_time_end or expected_intent.latest_time_end
        ) and not intent.basic_information.area.time_end:
            raise ValueError(
                f"Flight intent `{expected_intent.intent_id}` has a time_end bound requirement but has no time_end specified"
            )

        if expected_intent.earliest_time_start:
            min_start_time = (
                now.datetime + expected_intent.earliest_time_start.timedelta
            )
            if intent.basic_information.area.time_start.datetime < min_start_time:
                raise ValueError(
                    f"Flight intent `{expected_intent.intent_id}` must have time_start ({intent.basic_information.area.time_start.datetime}) >= min_start_time ({min_start_time})"
                )
        if expected_intent.latest_time_start:
            max_start_time = now.datetime + expected_intent.latest_time_start.timedelta
            if intent.basic_information.area.time_start.datetime > max_start_time:
                raise ValueError(
                    f"Flight intent `{expected_intent.intent_id}` must have time_start ({intent.basic_information.area.time_start.datetime}) <= max_start_time ({max_start_time})"
                )
        if expected_intent.earliest_time_end:
            min_end_time = now.datetime + expected_intent.earliest_time_end.timedelta
            if intent.basic_information.area.time_end.datetime < min_end_time:
                raise ValueError(
                    f"Flight intent `{expected_intent.intent_id}` must have time_end ({intent.basic_information.area.time_end.datetime}) >= min_end_time ({min_end_time})"
                )
        if expected_intent.latest_time_end:
            max_end_time = now.datetime + expected_intent.latest_time_end.timedelta
            if intent.basic_information.area.time_end.datetime > max_end_time:
                raise ValueError(
                    f"Flight intent `{expected_intent.intent_id}` must have time_end ({intent.basic_information.area.time_end.datetime}) <= max_end_time ({max_end_time})"
                )

        # Ensure flight authorisation data is (in)valid
        if expected_intent.valid_uspace_flight_auth is not None:
            problems = problems_with_flight_authorisation(
                intent.uspace_flight_authorisation
            )
            if expected_intent.valid_uspace_flight_auth and problems:
                raise ValueError(
                    f"Flight intent `{expected_intent.intent_id}` must have valid flight authorisation, instead it had: {problems}."
                )
            elif not expected_intent.valid_uspace_flight_auth and not problems:
                raise ValueError(
                    f"Flight intent `{expected_intent.intent_id}` must have invalid flight authorisation, instead it had valid flight authorisation data."
                )
