from dataclasses import dataclass
from datetime import timedelta
from typing import Optional, List, Dict, Iterator

import arrow

from monitoring.monitorlib.clients.flight_planning.flight_info import (
    AirspaceUsageState,
    UasState,
    FlightInfo,
)
from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    FlightInfoTemplate,
)
from monitoring.monitorlib.temporal import TimeDuringTest, Time
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntentID,
)

FlightIntentName = str

MAX_TEST_RUN_DURATION = timedelta(minutes=30)
"""The longest a test run might take (to estimate flight intent timestamps prior to scenario execution)"""


@dataclass
class ExpectedFlightIntent(object):
    intent_id: FlightIntentID
    name: FlightIntentName
    must_conflict_with: Optional[List[FlightIntentName]] = None
    must_not_conflict_with: Optional[List[FlightIntentName]] = None
    usage_state: Optional[AirspaceUsageState] = None
    uas_state: Optional[UasState] = None
    f3548v21_priority_higher_than: Optional[List[FlightIntentName]] = None
    f3548v21_priority_equal_to: Optional[List[FlightIntentName]] = None


def validate_flight_intent_templates(
    templates: Dict[FlightIntentID, FlightInfoTemplate],
    expected_intents: List[ExpectedFlightIntent],
) -> None:
    now = arrow.utcnow().datetime
    times = {
        TimeDuringTest.StartOfTestRun: Time(now),
        TimeDuringTest.StartOfScenario: Time(now),
        TimeDuringTest.TimeOfEvaluation: Time(now),
    }
    flight_intents = {k: v.resolve(times) for k, v in templates.items()}
    validate_flight_intents(flight_intents, expected_intents)

    later = now + MAX_TEST_RUN_DURATION
    times = {
        TimeDuringTest.StartOfTestRun: Time(now),
        TimeDuringTest.StartOfScenario: Time(later),
        TimeDuringTest.TimeOfEvaluation: Time(later),
    }
    flight_intents = {k: v.resolve(times) for k, v in templates.items()}
    validate_flight_intents(flight_intents, expected_intents)


def validate_flight_intents(
    intents: Dict[FlightIntentID, FlightInfo],
    expected_intents: List[ExpectedFlightIntent],
) -> None:
    """Validate that `intents` contains all intents meeting all the criteria in `expected_intents`.

    Args:
        intents: Flight intents we actually have.
        expected_intents: Criteria that our flight intents are expected to meet.

    Raises:
        * ValueError when a validation criterion is not met.
    """

    # Ensure all intents are present
    for expected_intent in expected_intents:
        if expected_intent.intent_id not in intents:
            raise ValueError(f"Missing flight intent `{expected_intent.intent_id}`")

    for expected_intent in expected_intents:
        intent = intents[expected_intent.intent_id]

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
