from typing import Optional, List

import arrow

from monitoring.monitorlib.geotemporal import Volume4DCollection
from monitoring.uss_qualifier.common_data_definitions import Severity
from uas_standards.astm.f3548.v21.api import OperationalIntentState
from uas_standards.interuss.automated_testing.scd.v1.api import (
    InjectFlightResponseResult,
)

from monitoring.uss_qualifier.resources.astm.f3548.v21 import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.resources.flight_planning import (
    FlightIntentsResource,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntent,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_planner import (
    FlightPlanner,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_planners import (
    FlightPlannerResource,
)
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import (
    OpIntentValidator,
    set_uss_available,
    set_uss_down,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    cleanup_flights,
    submit_flight_intent,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class DownUSS(TestScenario):
    flight_1_id: Optional[str] = None
    flight_1_planned_vol_A: FlightIntent

    flight_2_planned_vol_A: FlightIntent

    uss_qualifier_sub: str

    tested_uss: FlightPlanner
    dss: DSSInstance

    def __init__(
        self,
        flight_intents: FlightIntentsResource,
        tested_uss: FlightPlannerResource,
        dss: DSSInstanceResource,
    ):
        super().__init__()
        self.tested_uss = tested_uss.flight_planner
        self.dss = dss.dss

        _flight_intents = {
            k: FlightIntent.from_flight_info_template(v)
            for k, v in flight_intents.get_flight_intents().items()
        }

        extents = []
        for intent in _flight_intents.values():
            extents.extend(intent.request.operational_intent.volumes)
            extents.extend(intent.request.operational_intent.off_nominal_volumes)
        self._intents_extent = Volume4DCollection.from_interuss_scd_api(
            extents
        ).bounding_volume.to_f3548v21()

        try:
            (self.flight_1_planned_vol_A, self.flight_2_planned_vol_A,) = (
                _flight_intents["flight_1_planned_vol_A"],
                _flight_intents["flight_2_planned_vol_A"],
            )

            now = arrow.utcnow().datetime
            for intent_name, intent in _flight_intents.items():
                if (
                    intent.request.operational_intent.state
                    == OperationalIntentState.Activated
                ):
                    assert Volume4DCollection.from_interuss_scd_api(
                        intent.request.operational_intent.volumes
                        + intent.request.operational_intent.off_nominal_volumes
                    ).has_active_volume(
                        now
                    ), f"at least one volume of activated intent {intent_name} must be active now (now is {now})"

            assert (
                self.flight_1_planned_vol_A.request.operational_intent.state
                == OperationalIntentState.Accepted
            ), "flight_1_planned_vol_A must have state Accepted"
            assert (
                self.flight_2_planned_vol_A.request.operational_intent.state
                == OperationalIntentState.Accepted
            ), "flight_2_planned_vol_A must have state Accepted"

            # TODO: check that flight data is the same across the different versions of the flight

            assert (
                self.flight_2_planned_vol_A.request.operational_intent.priority
                > self.flight_1_planned_vol_A.request.operational_intent.priority
            ), "flight_2 must have higher priority than flight_1"
            assert Volume4DCollection.from_interuss_scd_api(
                self.flight_1_planned_vol_A.request.operational_intent.volumes
            ).intersects_vol4s(
                Volume4DCollection.from_interuss_scd_api(
                    self.flight_2_planned_vol_A.request.operational_intent.volumes
                )
            ), "flight_1_planned_vol_A and flight_2_planned_vol_A must intersect"

        except KeyError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: missing flight intent {e}"
            )
        except AssertionError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: {e}"
            )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.record_note(
            "Tested USS",
            f"{self.tested_uss.config.participant_id}",
        )

        self.begin_test_case("Setup")
        self._setup()
        self.end_test_case()

        self.begin_test_case(
            "Plan flight in conflict with planned flight managed by down USS"
        )
        self._plan_flight_conflict_planned()
        self.end_test_case()

        self.end_test_scenario()

    def _setup(self):

        self.begin_test_step("Resolve USS ID of virtual USS")
        _, dummy_query = self.dss.find_op_intent(self._intents_extent)
        with self.check("Successful dummy query", [self.dss.participant_id]) as check:
            if dummy_query.status_code != 200:
                check.record_failed(
                    summary="Failed to query DSS",
                    severity=Severity.High,
                    details=f"DSS responded code {dummy_query.status_code}; error message: {dummy_query.error_message}",
                    query_timestamps=[dummy_query.request.timestamp],
                )
        self.uss_qualifier_sub = self.dss.client.auth_adapter.get_sub()
        self.record_note(
            "USS ID of virtual USS",
            f"{self.uss_qualifier_sub}",
        )
        self.end_test_step()

        set_uss_available(
            self, "Restore virtual USS availability", self.dss, self.uss_qualifier_sub
        )

        self.begin_test_step("Clear operational intents created by virtual USS")
        self._clear_op_intents()
        self.end_test_step()

    def _plan_flight_conflict_planned(self):

        # Virtual USS plans high-priority flight 2 test step
        self.begin_test_step("Virtual USS plans high-priority flight 2")
        oi_ref, _, query = self.dss.put_op_intent(
            Volume4DCollection.from_interuss_scd_api(
                self.flight_2_planned_vol_A.request.operational_intent.volumes
            ).to_f3548v21(),
            [],  # we assume there is no other operational intent in that area
            OperationalIntentState.Accepted,
            "https://fake.uss/down",
        )
        self.record_query(query)
        with self.check(
            "Operational intent successfully created", [self.dss.participant_id]
        ) as check:
            if oi_ref is None:
                check.record_failed(
                    "Operational intent not successfully created",
                    Severity.High,
                    f"DSS responded code {query.status_code}; error message: {query.json_result['message']}",
                    query_timestamps=[query.request.timestamp],
                )
        self.end_test_step()

        # Declare virtual USS as down at DSS test step
        set_uss_down(
            self, "Declare virtual USS as down at DSS", self.dss, self.uss_qualifier_sub
        )

        # Tested USS attempts to plan low-priority flight 1 test step
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate low-priority flight 1 status",
            self._intents_extent,
        ) as validator:
            expected_results = {
                InjectFlightResponseResult.Planned,
                # the following two results are considered expected in order to fail another check as low severity
                InjectFlightResponseResult.Rejected,
                InjectFlightResponseResult.ConflictWithFlight,
            }
            failed_checks = {
                InjectFlightResponseResult.Failed: "Failure",
                InjectFlightResponseResult.Rejected: (
                    "Rejected planning",
                    Severity.Low,
                ),
                InjectFlightResponseResult.ConflictWithFlight: (
                    "Rejected planning",
                    Severity.Low,
                ),
            }

            resp, flight_id = submit_flight_intent(
                self,
                "Tested USS attempts to plan low-priority flight 1",
                "Successful planning",
                expected_results,
                failed_checks,
                self.tested_uss,
                self.flight_1_planned_vol_A.request,
            )

            if resp.result == InjectFlightResponseResult.Planned:
                validator.expect_shared(self.flight_1_planned_vol_A.request)
            elif (
                resp.result == InjectFlightResponseResult.Rejected
                or resp.result == InjectFlightResponseResult.ConflictWithFlight
            ):
                validator.expect_not_shared()

    def _clear_op_intents(self):
        oi_refs, find_query = self.dss.find_op_intent(self._intents_extent)
        self.record_query(find_query)

        with self.check(
            "Successful operational intents cleanup", [self.dss.participant_id]
        ) as check:
            if find_query.status_code != 200:
                check.record_failed(
                    summary=f"Failed to query operational intents from DSS in {self._intents_extent} for cleanup",
                    severity=Severity.High,
                    details=f"DSS responded code {find_query.status_code}; error message: {find_query.error_message}",
                    query_timestamps=[find_query.request.timestamp],
                )

            for oi_ref in oi_refs:
                if (
                    oi_ref.ovn is not None
                ):  # if the OVN is specified, this op intent belongs to our virtual USS
                    del_oi, _, del_query = self.dss.delete_op_intent(
                        oi_ref.id, oi_ref.ovn
                    )
                    self.record_query(del_query)

                    if del_oi is None:
                        check.record_failed(
                            summary=f"Failed to delete op intent {oi_ref.id} from DSS",
                            severity=Severity.Medium,
                            details=f"DSS responded code {del_query.status_code}; error message: {del_query.error_message}",
                            query_timestamps=[del_query.request.timestamp],
                        )

    def cleanup(self):
        self.begin_cleanup()

        with self.check(
            "Availability of virtual USS restored", [self.dss.participant_id]
        ) as check:
            availability_version, avail_query = self.dss.set_uss_availability(
                self.uss_qualifier_sub,
                True,
            )
            self.record_query(avail_query)
            if availability_version is None:
                check.record_failed(
                    summary=f"Availability of USS {self.uss_qualifier_sub} could not be set to available",
                    severity=Severity.High,
                    details=f"DSS responded code {avail_query.status_code}; error message: {avail_query.error_message}",
                    query_timestamps=[avail_query.request.timestamp],
                )

        cleanup_flights(self, [self.tested_uss])
        self._clear_op_intents()

        self.end_cleanup()
