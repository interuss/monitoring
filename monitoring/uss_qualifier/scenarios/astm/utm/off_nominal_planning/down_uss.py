from typing import Dict, Optional

import arrow

from monitoring.monitorlib.geotemporal import Volume4DCollection
from monitoring.uss_qualifier.common_data_definitions import Severity
from uas_standards.astm.f3548.v21.api import (
    OperationalIntentState,
    OperationalIntentReference,
)
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
    flight1_planned: FlightIntent

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

        _flight_intents: Dict[str, FlightIntent] = {
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

        now = arrow.utcnow().datetime
        for intent_name, intent in _flight_intents.items():
            if (
                intent.request.operational_intent.state
                == OperationalIntentState.Activated
            ):
                if not Volume4DCollection.from_interuss_scd_api(
                    intent.request.operational_intent.volumes
                    + intent.request.operational_intent.off_nominal_volumes
                ).has_active_volume(now):
                    err_msg = f"at least one volume of activated intent {intent_name} must be active now (now is {now})"
                    raise ValueError(
                        f"`{self.me()}` TestScenario requirements for flight_intents not met: {err_msg}"
                    )

        self._parse_flight_intents(_flight_intents)

    def _parse_flight_intents(self, flight_intents: Dict[str, FlightIntent]) -> None:
        try:
            self.flight1_planned = flight_intents["flight1_planned"]

            assert (
                self.flight1_planned.request.operational_intent.state
                == OperationalIntentState.Accepted
            ), "flight1_planned must have state Accepted"

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
            "Plan Flight 1 in conflict with accepted operational intent managed by down USS"
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

        self.begin_test_step("Restore virtual USS availability")
        set_uss_available(self, self.dss, self.uss_qualifier_sub)
        self.end_test_step()

        self.begin_test_step("Clear operational intents created by virtual USS")
        self._clear_op_intents()
        self.end_test_step()

    def _put_conflicting_op_intent_step(
        self,
        conflicting_intent: FlightIntent,
        target_state: OperationalIntentState,
        old_op_intent: Optional[OperationalIntentReference] = None,
    ) -> OperationalIntentReference:
        if old_op_intent is not None:
            key = [old_op_intent.ovn]
            oi_id = old_op_intent.id
            oi_ovn = old_op_intent.ovn
        else:
            key = None
            oi_id = None
            oi_ovn = None

        if target_state == OperationalIntentState.Accepted:
            msg_action = "creates"
            msg_action_past = "created"
        elif target_state == OperationalIntentState.Activated:
            msg_action = "activates"
            msg_action_past = "activated"
        elif target_state == OperationalIntentState.Nonconforming:
            msg_action = "transitions to Nonconforming"
            msg_action_past = "transitioned to Nonconforming"
        elif target_state == OperationalIntentState.Contingent:
            msg_action = "transitions to Contingent"
            msg_action_past = "transitioned to Contingent"
        else:
            raise ValueError(f"Invalid state {target_state}")

        self.begin_test_step(f"Virtual USS {msg_action} conflicting operational intent")
        oi_ref, _, query = self.dss.put_op_intent(
            Volume4DCollection.from_interuss_scd_api(
                conflicting_intent.request.operational_intent.volumes
            ).to_f3548v21(),
            key,
            target_state,
            "https://fake.uss/down",
            oi_id,
            oi_ovn,
        )
        self.record_query(query)
        with self.check(
            f"Operational intent successfully {msg_action_past}",
            [self.dss.participant_id],
        ) as check:
            if oi_ref is None:
                check.record_failed(
                    f"Operational intent not successfully {msg_action_past}",
                    Severity.High,
                    f"DSS responded code {query.status_code}; error message: {query.error_message}",
                    query_timestamps=[query.request.timestamp],
                )
        self.end_test_step()
        return oi_ref

    def _plan_flight_conflict_planned(self):

        # Virtual USS creates conflicting operational intent test step
        self._put_conflicting_op_intent_step(
            self.flight1_planned, OperationalIntentState.Accepted
        )

        # Declare virtual USS as down at DSS test step
        self.begin_test_step("Declare virtual USS as down at DSS")
        set_uss_down(self, self.dss, self.uss_qualifier_sub)
        self.end_test_step()

        # Tested USS attempts to plan Flight 1 test step
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            "Validate Flight 1 status",
            self._intents_extent,
        ) as validator:
            self.begin_test_step("Tested USS attempts to plan Flight 1")
            resp, flight_id, _ = submit_flight_intent(
                self,
                "Successful planning",
                {
                    InjectFlightResponseResult.Planned,
                    # the following two results are considered expected in order to fail another check as low severity
                    InjectFlightResponseResult.Rejected,
                    InjectFlightResponseResult.ConflictWithFlight,
                },
                {
                    InjectFlightResponseResult.Failed: "Failure",
                },
                self.tested_uss,
                self.flight1_planned.request,
            )

            if resp.result == InjectFlightResponseResult.Planned:
                self.end_test_step()
                validator.expect_shared(self.flight1_planned.request)
            elif (
                resp.result == InjectFlightResponseResult.Rejected
                or resp.result == InjectFlightResponseResult.ConflictWithFlight
            ):
                with self.check(
                    "Rejected planning", [self.tested_uss.participant_id]
                ) as check:
                    check_details = (
                        f"{self.tested_uss.participant_id} indicated {resp.result}"
                        + f' with notes "{resp.notes}"'
                        if "notes" in resp and resp.notes
                        else " with no notes"
                    )
                    check.record_failed(
                        summary="Warning (not a failure): planning got rejected, USS may have been more conservative",
                        severity=Severity.Low,
                        details=check_details,
                    )
                self.end_test_step()
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
