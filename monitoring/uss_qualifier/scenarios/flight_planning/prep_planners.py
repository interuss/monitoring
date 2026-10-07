from datetime import timedelta

import arrow

from monitoring.monitorlib.clients.flight_planning.client import (
    FlightPlannerClient,
    PlanningActivityError,
)
from monitoring.monitorlib.geotemporal import Volume4D, Volume4DCollection
from monitoring.monitorlib.temporal import TestTimeContext, Time
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources.flight_planning import (
    FlightIntentsResource,
    FlightPlannersResource,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntentsSpecification,
)
from monitoring.uss_qualifier.resources.interuss.mock_uss.client import MockUSSResource
from monitoring.uss_qualifier.resources.resource import ResourceProvidingResource
from monitoring.uss_qualifier.scenarios.scenario import TestScenario

MAX_TEST_DURATION = timedelta(minutes=45)
"""The maximum time the tests depending on the area being clear might last."""


class PrepareFlightPlannersScenario(TestScenario):
    areas: list[Volume4D]
    flight_planners: dict[ParticipantID, FlightPlannerClient]

    def __init__(
        self,
        flight_planners: FlightPlannersResource,
        flight_intents: FlightIntentsResource,
        mock_uss: MockUSSResource | None = None,
        flight_intents2: FlightIntentsResource | None = None,
        flight_intents3: FlightIntentsResource | None = None,
        flight_intents4: FlightIntentsResource | None = None,
        flight_intents_provider: ResourceProvidingResource[
            FlightIntentsSpecification, FlightIntentsResource
        ]
        | None = None,
    ):
        super().__init__()
        now = Time(arrow.utcnow().datetime)
        times_now = TestTimeContext.all_times_are(now)
        later = now.offset(MAX_TEST_DURATION)
        times_later = TestTimeContext.all_times_are(later)
        self.areas = []
        if flight_intents_provider:
            # TODO: use just the indices that will be used in the test run
            # This can be accomplished by creating a
            # ResourceCombinationsResource[T1: Resource](Resource[ResourceCombinationsSpecification])
            # whose `source` is a PluralResource[T1] abstract base class (implemented by, e.g.,
            # FlightPlannersResource).  ResourceCombinationsResource will fill a specified number
            # of roles with combinations of resources (producing list[dict[ResourceID, T1]])
            # just like, e.g. the FlightPlannerCombinations action generator currently.  Then,
            # FlightPlannerCombinations can be adjusted to accept a ResourceCombinationsResource
            # with all the combinations pregenerated -- this achieves parity with today, just the
            # combinations are produced in the ResourceCombinationsResource rather than the action
            # generator.  Then, we can have a PerCombinationResources[T2: Resource] that uses the
            # ResourceCombinationsResource as a dependency and produces a FlightIntentsResource per
            # combination.  That PerCombinationResources will implement PluralResource[T2], and
            # then this scenario can be adjusted to accept a PluralResource[FlightIntentsResource]
            # instead of the ResourceProvidingResource[FlightIntentsResource].
            extra_intents = (flight_intents_provider.provide_resource_for(index=0),)
        else:
            extra_intents = tuple()
        for intents in (
            flight_intents,
            flight_intents2,
            flight_intents3,
            flight_intents4,
        ) + extra_intents:
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
                            query_timestamps=[
                                q.request.timestamp for q in resp.queries
                            ],
                        )
