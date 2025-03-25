from typing import Dict, List, Optional

import arrow
from uas_standards.astm.f3548.v21.api import (
    OperationalIntentReference,
    OperationalIntentState,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.clients.flight_planning.client import FlightPlannerClient
from monitoring.monitorlib.clients.flight_planning.flight_info import (
    AirspaceUsageState,
    FlightInfo,
    UasState,
)
from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    FlightInfoTemplate,
)
from monitoring.monitorlib.clients.flight_planning.planning import (
    FlightPlanStatus,
    PlanningActivityResult,
)
from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.temporal import Time, TimeDuringTest
from monitoring.monitorlib.testing import make_fake_url
from monitoring.uss_qualifier.resources.astm.f3548.v21 import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.resources.flight_planning import FlightIntentsResource
from monitoring.uss_qualifier.resources.flight_planning.flight_intent_validation import (
    ExpectedFlightIntent,
    validate_flight_intent_templates,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_planners import (
    FlightPlannerResource,
)
from monitoring.uss_qualifier.scenarios.astm.utm.clear_area_validation import (
    validate_clear_area,
)
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import (
    OpIntentValidator,
    set_uss_available,
    set_uss_down,
)
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    cleanup_flights,
    submit_flight,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class DownUSS(TestScenario):
    times: Dict[TimeDuringTest, Time]

    flight1_planned: FlightInfoTemplate

    uss_qualifier_sub: str

    tested_uss: FlightPlannerClient
    dss_resource: DSSInstanceResource
    dss: DSSInstance

    def __init__(
        self,
        flight_intents: FlightIntentsResource,
        tested_uss: FlightPlannerResource,
        dss: DSSInstanceResource,
    ):
        super().__init__()
        self.tested_uss = tested_uss.client
        self.dss = dss.get_instance(self._dss_req_scopes)

        templates = flight_intents.get_flight_intents()
        try:
            self._intents_extent = validate_flight_intent_templates(
                templates, self._expected_flight_intents
            )
        except ValueError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: {e}"
            )

        for efi in self._expected_flight_intents:
            setattr(self, efi.intent_id, templates[efi.intent_id])

    @property
    def _dss_req_scopes(self) -> dict[str, str]:
        return {
            Scope.StrategicCoordination: "search for operational intent references to verify outcomes of planning activities and retrieve operational intent details",
            Scope.AvailabilityArbitration: "declare virtual USS down in DSS",
        }

    @property
    def _expected_flight_intents(self) -> List[ExpectedFlightIntent]:
        return [
            ExpectedFlightIntent(
                "flight1_planned",
                "Flight 1",
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
            )
        ]

    def resolve_flight(self, flight_template: FlightInfoTemplate) -> FlightInfo:
        self.times[TimeDuringTest.TimeOfEvaluation] = Time(arrow.utcnow().datetime)
        return flight_template.resolve(self.times)

    def run(self, context: ExecutionContext):
        self.times = {
            TimeDuringTest.StartOfTestRun: Time(context.start_time),
            TimeDuringTest.StartOfScenario: Time(arrow.utcnow().datetime),
        }

        self.begin_test_scenario(context)

        self.record_note(
            "Tested USS",
            f"{self.tested_uss.participant_id}",
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
        with self.check("Successful dummy query", [self.dss.participant_id]) as check:
            try:
                _, dummy_query = self.dss.find_op_intent(
                    self._intents_extent.to_f3548v21()
                )
                self.record_query(dummy_query)
            except QueryError as e:
                self.record_queries(e.queries)
                dummy_query = e.queries[0]
                check.record_failed(
                    summary="Failed to query DSS",
                    details=f"DSS responded code {dummy_query.status_code}; {e}",
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

        self.begin_test_step("Verify area is clear")
        validate_clear_area(
            self,
            self.dss,
            [self._intents_extent],
            ignore_self=True,
        )
        self.end_test_step()

    def _put_conflicting_op_intent_step(
        self,
        conflicting_flight: FlightInfo,
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
        with self.check(
            f"Operational intent successfully {msg_action_past}",
            [self.dss.participant_id],
        ) as check:
            try:
                oi_ref, _, query = self.dss.put_op_intent(
                    conflicting_flight.basic_information.area.to_f3548v21(),
                    key,
                    target_state,
                    make_fake_url("down"),
                    oi_id,
                    oi_ovn,
                )
                self.record_query(query)
            except QueryError as e:
                self.record_queries(e.queries)
                query = e.queries[0]
                check.record_failed(
                    f"Operational intent not successfully {msg_action_past}",
                    details=f"DSS responded code {query.status_code}; {e}",
                    query_timestamps=[query.request.timestamp],
                )
        self.end_test_step()
        return oi_ref

    def _plan_flight_conflict_planned(self):

        # Virtual USS creates conflicting operational intent test step
        flight1_planned = self.resolve_flight(self.flight1_planned)
        self._put_conflicting_op_intent_step(
            flight1_planned, OperationalIntentState.Accepted
        )

        # Declare virtual USS as down at DSS test step
        self.begin_test_step("Declare virtual USS as down at DSS")
        set_uss_down(self, self.dss, self.uss_qualifier_sub)
        self.end_test_step()

        # Tested USS attempts to plan Flight 1 test step
        self.begin_test_step("Tested USS attempts to plan Flight 1")
        with OpIntentValidator(
            self,
            self.tested_uss,
            self.dss,
            flight1_planned,
        ) as validator:
            resp, flight_id = submit_flight(
                scenario=self,
                success_check="Successful planning",
                expected_results={
                    (PlanningActivityResult.Completed, FlightPlanStatus.Planned),
                    # the following result is considered expected in order to fail another check as low severity
                    (PlanningActivityResult.Rejected, FlightPlanStatus.NotPlanned),
                },
                failed_checks={PlanningActivityResult.Failed: "Failure"},
                flight_planner=self.tested_uss,
                flight_info=flight1_planned,
            )

            if resp.activity_result == PlanningActivityResult.Completed:
                validator.expect_shared(flight1_planned)
            elif resp.activity_result == PlanningActivityResult.Rejected:
                with self.check(
                    "Rejected planning", [self.tested_uss.participant_id]
                ) as check:
                    msg = f"{self.tested_uss.participant_id} indicated {resp.activity_result}"
                    if "notes" in resp and resp.notes:
                        msg += f' with notes "{resp.notes}"'
                    else:
                        msg += " with no notes"
                    check.record_failed(
                        summary="Warning (not a failure): planning got rejected, USS may have been more conservative",
                        details=msg,
                    )
                validator.expect_not_shared()
        self.end_test_step()

    def _clear_op_intents(self):

        with self.check(
            "Successful operational intents cleanup", [self.dss.participant_id]
        ) as check:
            try:
                oi_refs, find_query = self.dss.find_op_intent(
                    self._intents_extent.to_f3548v21()
                )
                self.record_query(find_query)
            except QueryError as e:
                self.record_queries(e.queries)
                find_query = e.queries[0]
                check.record_failed(
                    summary=f"Failed to query operational intent references from DSS in {self._intents_extent} for cleanup",
                    details=f"DSS responded code {find_query.status_code}; {e}",
                    query_timestamps=[find_query.request.timestamp],
                )

            for oi_ref in oi_refs:
                if oi_ref.manager == self.uss_qualifier_sub:
                    try:
                        del_oi, _, del_query = self.dss.delete_op_intent(
                            oi_ref.id, oi_ref.ovn
                        )
                        self.record_query(del_query)
                    except QueryError as e:
                        self.record_queries(e.queries)
                        del_query = e.queries[0]
                        check.record_failed(
                            summary=f"Failed to delete op intent {oi_ref.id} from DSS",
                            details=f"DSS responded code {del_query.status_code}; {e}",
                            query_timestamps=[del_query.request.timestamp],
                        )

    def cleanup(self):
        self.begin_cleanup()

        with self.check(
            "Availability of virtual USS restored", [self.dss.participant_id]
        ) as check:
            try:
                availability_version, avail_query = self.dss.set_uss_availability(
                    self.uss_qualifier_sub,
                    True,
                )
                self.record_query(avail_query)
            except QueryError as e:
                self.record_queries(e.queries)
                avail_query = e.queries[0]
                check.record_failed(
                    summary=f"Availability of USS {self.uss_qualifier_sub} could not be set to available",
                    details=f"DSS responded code {avail_query.status_code}; {e}",
                    query_timestamps=[avail_query.request.timestamp],
                )

        cleanup_flights(self, [self.tested_uss])
        self._clear_op_intents()

        self.end_cleanup()
