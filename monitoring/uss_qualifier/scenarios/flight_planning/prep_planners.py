from datetime import timedelta
from typing import Optional, Dict, List

import arrow

from monitoring.monitorlib.clients.flight_planning.client import (
    FlightPlannerClient,
    PlanningActivityError,
)
from monitoring.monitorlib.geotemporal import Volume4DCollection, Volume4D
from monitoring.monitorlib.temporal import Time, TimeDuringTest
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources.flight_planning import (
    FlightPlannersResource,
    FlightIntentsResource,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import (
    MockUSSResource,
)

MAX_TEST_DURATION = timedelta(minutes=15)
"""The maximum time the tests depending on the area being clear might last."""


class PrepareFlightPlanners(TestScenario):
    areas: List[Volume4D]
    flight_planners: Dict[ParticipantID, FlightPlannerClient]

    def __init__(
        self,
        flight_planners: FlightPlannersResource,
        flight_intents: FlightIntentsResource,
        mock_uss: Optional[MockUSSResource] = None,
        flight_intents2: Optional[FlightIntentsResource] = None,
        flight_intents3: Optional[FlightIntentsResource] = None,
        flight_intents4: Optional[FlightIntentsResource] = None,
    ):
        super().__init__()
        now = Time(arrow.utcnow().datetime)
        times_now = {t: now for t in TimeDuringTest}
        later = now.offset(MAX_TEST_DURATION)
        times_later = {t: later for t in TimeDuringTest}
        self.areas = []
        for intents in (
            flight_intents,
            flight_intents2,
            flight_intents3,
            flight_intents4,
        ):
            if intents is None:
                continue
            v4c = Volume4DCollection([])
            for flight_info_template in intents.get_flight_intents().values():
                v4c.extend(
                    flight_info_template.resolve(times_now).basic_information.area
                )
                v4c.extend(
                    flight_info_template.resolve(times_later).basic_information.area
                )
            self.areas.append(v4c.bounding_volume)
        self.flight_planners = {
            fp.participant_id: fp.client for fp in flight_planners.flight_planners
        }
        if mock_uss is not None:
            self.flight_planners.update(
                {mock_uss.mock_uss.participant_id: mock_uss.mock_uss.flight_planner}
            )

    def run(self, context):
        self.begin_test_scenario(context)
        self.begin_test_case("Preparation")

        self.begin_test_step("Check for flight planning readiness")
        self._check_readiness()
        self.end_test_step()

        self.begin_test_step("Area clearing")
        self._clear_area()
        self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def _check_readiness(self):
        for participant_id, client in self.flight_planners.items():
            with self.check(
                "Valid response to readiness query", [participant_id]
            ) as check:
                try:
                    resp = client.report_readiness()
                except PlanningActivityError as e:
                    for q in e.queries:
                        self.record_query(q)
                    check.record_failed(
                        summary=f"Error while determining readiness of {participant_id}",
                        details=str(e),
                        severity=Severity.Medium,
                        query_timestamps=[q.request.timestamp for q in e.queries],
                    )
                    continue
            for q in resp.queries:
                self.record_query(q)
            with self.check("Flight planning USS ready", [participant_id]) as check:
                if resp.errors:
                    check.record_failed(
                        summary=f"Errors in {participant_id} readiness",
                        details="\n".join("* " + e for e in resp.errors),
                        severity=Severity.Medium,
                        query_timestamps=[q.request.timestamp for q in resp.queries],
                    )

    def _clear_area(self):
        for area in self.areas:
            for participant_id, client in self.flight_planners.items():
                with self.check(
                    "Valid response to clearing query", [participant_id]
                ) as check:
                    try:
                        resp = client.clear_area(area)
                    except PlanningActivityError as e:
                        for q in e.queries:
                            self.record_query(q)
                        check.record_failed(
                            summary=f"Error while instructing {participant_id} to clear area",
                            details=str(e),
                            severity=Severity.Medium,
                            query_timestamps=[q.request.timestamp for q in e.queries],
                        )
                        continue
                for q in resp.queries:
                    self.record_query(q)
                with self.check("Area cleared successfully", [participant_id]) as check:
                    if resp.errors:
                        check.record_failed(
                            summary=f"Errors when {participant_id} was clearing the area",
                            details="\n".join("* " + e for e in resp.errors),
                            severity=Severity.Medium,
                            query_timestamps=[
                                q.request.timestamp for q in resp.queries
                            ],
                        )
