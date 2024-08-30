from typing import List, Dict

import arrow
from uas_standards.astm.f3548.v21 import api as f3548v21
from uas_standards.astm.f3548.v21.api import OperationalIntentState
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    FlightInfoTemplate,
)
from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.temporal import TimeDuringTest, Time
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources.astm.f3548.v21 import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstance,
    DUMMY_USS_BASE_URL,
)
from monitoring.uss_qualifier.resources.flight_planning import FlightIntentsResource
from monitoring.uss_qualifier.resources.flight_planning.flight_intent_validation import (
    ExpectedFlightIntent,
    validate_flight_intent_templates,
)
from monitoring.uss_qualifier.resources.interuss import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class OpIntentReferenceStateTransitions(TestScenario):
    """
    Tests that a DSS only permits allowed state transitions of operational intent references.

    Especially, it ensures that transitions to off-nominal states (Nonconforming and Contingent) can
    only be done by clients with the correct scope.
    """

    OP_INTENT = register_resource_type(389, "Operational Intent Reference")

    # The DSS under test
    _dss: DSSInstance
    _pid: List[str]

    # Participant IDs of users using this DSS instance
    _uids: List[str]

    _flight: FlightInfoTemplate

    _current_ref: f3548v21.OperationalIntentReference

    def __init__(
        self,
        flight_intents: FlightIntentsResource,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
    ):
        super().__init__()
        scopes = {
            Scope.StrategicCoordination: "create and delete operational intent references"
        }
        self._dss = dss.get_instance(scopes)
        self._pid = [self._dss.participant_id]
        self._uids = self._dss.user_participant_ids

        self._oid = id_generator.id_factory.make_id(self.OP_INTENT)

        expected_flight_intents = [
            ExpectedFlightIntent(
                "flight_1",
                "Flight 1",
            ),
        ]

        templates = flight_intents.get_flight_intents()
        try:
            validate_flight_intent_templates(templates, expected_flight_intents)
        except ValueError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: {e}"
            )
        self._flight = templates["flight_1"]

    def run(self, context: ExecutionContext):
        times = {
            TimeDuringTest.StartOfTestRun: Time(context.start_time),
            TimeDuringTest.StartOfScenario: Time(arrow.utcnow().datetime),
        }
        self.begin_test_scenario(context)
        self.begin_test_case("Setup")

        self.begin_test_step("Ensure clean workspace")
        times[TimeDuringTest.TimeOfEvaluation] = Time(arrow.utcnow().datetime)
        ws_is_clean = self._ensure_clean_workspace(times)
        self.end_test_step()
        self.end_test_case()

        if ws_is_clean:

            self.begin_test_case("Attempt unauthorized state creation")

            self.begin_test_step("Attempt direct creation with unauthorized state")
            self._check_unauthorized_state_creation(times)
            self.end_test_step()
            self.end_test_case()

            self.begin_test_case("Attempt unauthorized state transitions")

            self._steps_check_unauthorized_state_transitions(times)

            self.end_test_case()
        else:
            self.record_note(
                "clean_workspace",
                "Could not clean up workspace, skipping scenario",
            )

        self.end_test_scenario()

    def _get_extents(self, times: Dict[TimeDuringTest, Time]) -> Volume4D:
        return self._flight.resolve(times).basic_information.area.bounding_volume

    def _clean_known_op_intents_ids(self):
        with self.check(
            "Operational intent references can be queried by ID",
            self._pid,
        ) as check:
            try:
                (oi_ref, q) = self._dss.get_op_intent_reference(self._oid)
                self.record_query(q)
            except QueryError as e:
                self.record_queries(e.queries)
                q = e.queries[0]
                # If the Op Intent does not exist, it's fine to run into a 404.
                if q.response.status_code != 404:
                    check.record_failed(
                        f"Could not access operational intent using main credentials",
                        details=f"DSS responded with {q.response.status_code} to attempt to access OI {self._oid}; {e}",
                        query_timestamps=[q.request.timestamp],
                    )
        if q.response.status_code != 404:
            with self.check(
                "Operational intent reference removed",
                self._pid,
            ) as check:
                try:
                    (_, notifs, dq) = self._dss.delete_op_intent(self._oid, oi_ref.ovn)
                    self.record_query(dq)
                except QueryError as e:
                    self.record_queries(e.queries)
                    check.record_failed(
                        f"Could not delete operational intent using main credentials",
                        details=f"DSS responded with {e.cause_status_code} to attempt to delete OI {self._oid}; {e}",
                        query_timestamps=e.query_timestamps,
                    )

    def _attempt_to_delete_remaining_op_intents(
        self, times: Dict[TimeDuringTest, Time]
    ):
        """Search for op intents and attempt to delete them"""

        extent = self._get_extents(times)
        with self.check(
            "Operational intent references can be searched for",
            self._pid,
        ) as check:
            try:
                # Also check for any potential other op_intents and delete them
                (op_intents, q) = self._dss.find_op_intent(extent.to_f3548v21())
                self.record_query(q)
            except QueryError as e:
                self.record_queries(e.queries)
                q = e.queries[0]
                check.record_failed(
                    f"Could not search operational intent references",
                    details=f"DSS responded with {q.response.status_code} to attempt to search OIs; {e}",
                    query_timestamps=[q.request.timestamp],
                )

        for op_intent in op_intents:
            # We look for an op_intent where the uss_qualifier is the manager;
            if op_intent.manager == self._dss.client.auth_adapter.get_sub():
                with self.check(
                    "Operational intent reference removed",
                    self._pid,
                ) as check:
                    try:
                        (_, _, dq) = self._dss.delete_op_intent(
                            op_intent.id, op_intent.ovn
                        )
                        self.record_query(dq)
                    except QueryError as e:
                        self.record_queries(e.queries)
                        check.record_failed(
                            f"Could not delete operational intent reference",
                            details=f"DSS responded with {e.cause_status_code} to attempt to delete OI {op_intent.id}; {e}",
                            query_timestamps=e.query_timestamps,
                        )

    def _ensure_clean_workspace(self, times: Dict[TimeDuringTest, Time]) -> bool:
        """
        Tries to provide a clean workspace. If it fails to do so and the underlying check
        has a severity below HIGH, this function will return false.

        It will only return true if the workspace is clean.
        """
        extent = self._get_extents(times)

        # Delete what we know about
        self._clean_known_op_intents_ids()
        # Search and attempt deleting what may be found through search
        self._attempt_to_delete_remaining_op_intents(times)

        with self.check(
            "Operational intent references can be searched for",
            self._pid,
        ) as check:
            try:
                # We can't delete anything that would be left.
                (stray_oir, q) = self._dss.find_op_intent(extent.to_f3548v21())
                self.record_query(q)
            except QueryError as e:
                self.record_queries(e.queries)
                q = e.queries[0]
                check.record_failed(
                    f"Could not search operational intent references using main credentials",
                    details=f"DSS responded with {q.response.status_code} to attempt to search OIs; {e}",
                    query_timestamps=[q.request.timestamp],
                )

        with self.check(
            "Any existing operational intent reference has been removed", self._pid
        ) as check:
            if len(stray_oir) > 0:
                check.record_failed(
                    f"Found operational intents that cannot be cleaned up",
                    details=f"Operational intents that cannot be cleaned up were found: {stray_oir}",
                    query_timestamps=[q.request.timestamp],
                )
                return False

        return True

    def _check_unauthorized_state_creation(self, times: Dict[TimeDuringTest, Time]):
        times[TimeDuringTest.TimeOfEvaluation] = Time(arrow.utcnow().datetime)
        # Reuse info from flight 1 for the third Operational Intent Ref
        flight_3 = self._flight.resolve(times)
        with self.check(
            "Direct Nonconforming state creation is forbidden", self._pid + self._uids
        ) as check:
            try:
                (self._current_ref, subscribers, q) = self._dss.put_op_intent(
                    oi_id=self._oid,
                    extents=flight_3.basic_information.area.to_f3548v21(),
                    key=[],
                    state=OperationalIntentState.Nonconforming,
                    base_url=DUMMY_USS_BASE_URL,
                    # Force the query to use the SCD scope so the CMSA scope is not added
                    force_query_scopes=Scope.StrategicCoordination,
                )
                self.record_query(q)
                # If we reach this point, we should fail:
                check.record_failed(
                    f"Could create operational intent using main credentials",
                    details=f"DSS responded with {q.response.status_code} to attempt to create OI {self._oid}",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as e:
                self.record_queries(e.queries)
                if e.cause_status_code not in [400, 403]:
                    check.record_failed(
                        f"Forbidden operational intent reference creation failed with the wrong error code",
                        details=f"DSS responded with {e.cause_status_code} to attempt to create OI {self._oid} while 400 or 403 was expected; {e}",
                        query_timestamps=e.query_timestamps,
                    )

        with self.check(
            "Direct Contingent state creation is forbidden", self._pid + self._uids
        ) as check:
            try:
                (self._current_ref, subscribers, q) = self._dss.put_op_intent(
                    oi_id=self._oid,
                    extents=flight_3.basic_information.area.to_f3548v21(),
                    key=[],
                    state=OperationalIntentState.Contingent,
                    base_url=DUMMY_USS_BASE_URL,
                    # Force the query to use the SCD scope so the CMSA scope is not added
                    force_query_scopes=Scope.StrategicCoordination,
                )
                self.record_query(q)
                # If we reach this point, we should fail:
                check.record_failed(
                    f"Could create operational intent using main credentials",
                    details=f"DSS responded with {q.response.status_code} to attempt to create OI {self._oid_1}",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as e:
                self.record_queries(e.queries)
                if e.cause_status_code not in [400, 403]:
                    check.record_failed(
                        f"Forbidden operational intent reference creation failed with the wrong error code",
                        details=f"DSS responded with {e.cause_status_code} to attempt to create OI {self._oid} while 400 or 403 was expected; {e}",
                        query_timestamps=e.query_timestamps,
                    )

    def _steps_check_unauthorized_state_transitions(
        self, times: Dict[TimeDuringTest, Time]
    ):
        """This checks for UNAUTHORIZED state transitions, that is, transitions that require the correct scope,
        but are not otherwise disallowed by the standard."""

        self.begin_test_step("Create an Accepted OIR")

        times[TimeDuringTest.TimeOfEvaluation] = Time(arrow.utcnow().datetime)
        # Reuse info from flight 1 for the third Operational Intent Ref
        flight_extents = self._flight.resolve(
            times
        ).basic_information.area.to_f3548v21()

        with self.check("Creation of an Accepted OIR is allowed", self._pid) as check:
            try:
                (self._current_ref, subscribers, q) = self._dss.put_op_intent(
                    oi_id=self._oid,
                    extents=flight_extents,
                    key=[],
                    state=OperationalIntentState.Accepted,
                    base_url=DUMMY_USS_BASE_URL,
                )
                self.record_query(q)
            except QueryError as e:
                self.record_queries(e.queries)
                check.record_failed(
                    f"Could not create operational intent using main credentials",
                    details=f"DSS responded with {e.cause_status_code} to attempt to create OI {self._oid}; {e}",
                    query_timestamps=e.query_timestamps,
                )

        self.end_test_step()

        self.begin_test_step(
            "Attempt transition of an accepted operational intent reference to an unauthorized state"
        )

        with self.check(
            "Transition from Accepted to Nonconforming is forbidden",
            self._pid + self._uids,
        ) as check:
            try:
                (self._current_ref, subscribers, q) = self._dss.put_op_intent(
                    oi_id=self._oid,
                    extents=flight_extents,
                    key=[],
                    ovn=self._current_ref.ovn,
                    state=OperationalIntentState.Nonconforming,
                    base_url=DUMMY_USS_BASE_URL,
                    # Force the query to use the SCD scope so the CMSA scope is not added
                    force_query_scopes=Scope.StrategicCoordination,
                )
                self.record_query(q)
                check.record_failed(
                    "Transition from Accepted to Nonconforming was allowed using an improper scope",
                    details=f"DSS responded successfully to attempt to mutate OI {self._oid} from Accepted to Nonconforming",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as e:
                self.record_queries(e.queries)
                if e.cause_status_code not in [400, 403]:
                    check.record_failed(
                        f"Transition from Accepted to Nonconforming was rejected with wrong code",
                        details=f"DSS responded with {e.cause_status_code} to attempt to mutate OI {self._oid} while 403 was expected; {e}",
                        query_timestamps=e.query_timestamps,
                    )

        with self.check(
            "Transition from Accepted to Contingent is forbidden",
            self._pid + self._uids,
        ) as check:
            try:
                (self._current_ref, subscribers, q) = self._dss.put_op_intent(
                    oi_id=self._oid,
                    extents=flight_extents,
                    key=[],
                    ovn=self._current_ref.ovn,
                    state=OperationalIntentState.Nonconforming,
                    base_url=DUMMY_USS_BASE_URL,
                    # Force the query to use the SCD scope so the CMSA scope is not added
                    force_query_scopes=Scope.StrategicCoordination,
                )
                self.record_query(q)
                check.record_failed(
                    "Transition from Accepted to Contingent was allowed using an improper scope",
                    details=f"DSS responded successfully to attempt to mutate OI {self._oid} from Accepted to Contingent",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as e:
                self.record_queries(e.queries)
                if e.cause_status_code not in [400, 403]:
                    check.record_failed(
                        f"Transition from Accepted to Nonconforming was rejected with wrong code",
                        details=f"DSS responded with {e.cause_status_code} to attempt to mutate OI {self._oid} while 403 was expected; {e}",
                        query_timestamps=e.query_timestamps,
                    )

        self.end_test_step()

        self.begin_test_step("Transition the OIR to Activated")

        with self.check(
            "Transition from Accepted to Activated is allowed", self._pid
        ) as check:
            try:
                (self._current_ref, subscribers, q) = self._dss.put_op_intent(
                    oi_id=self._oid,
                    extents=flight_extents,
                    key=[],
                    ovn=self._current_ref.ovn,
                    state=OperationalIntentState.Activated,
                    base_url=DUMMY_USS_BASE_URL,
                )
                self.record_query(q)
            except QueryError as e:
                self.record_queries(e.queries)
                check.record_failed(
                    f"Transition from Accepted to Activated was wrongly rejected",
                    details=f"DSS responded with {e.cause_status_code} to attempt to transition OI {self._oid}; {e}",
                    query_timestamps=e.query_timestamps,
                )

        self.end_test_step()

        self.begin_test_step(
            "Attempt transition of an activated operational intent reference to an unauthorized state"
        )

        with self.check(
            "Transition from Activated to Nonconforming is forbidden",
            self._pid + self._uids,
        ) as check:
            try:
                (self._current_ref, subscribers, q) = self._dss.put_op_intent(
                    oi_id=self._oid,
                    extents=flight_extents,
                    key=[],
                    ovn=self._current_ref.ovn,
                    state=OperationalIntentState.Nonconforming,
                    base_url=DUMMY_USS_BASE_URL,
                    # Force the query to use the SCD scope so the CMSA scope is not added
                    force_query_scopes=Scope.StrategicCoordination,
                )
                self.record_query(q)
                check.record_failed(
                    "Transition from Activated to Nonconforming was allowed using an improper scope",
                    details=f"DSS responded successfully to attempt to mutate OI {self._oid} from Activated to Nonconforming",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as e:
                self.record_queries(e.queries)
                if e.cause_status_code not in [400, 403]:
                    check.record_failed(
                        f"Transition from Activated to Nonconforming was rejected with wrong code",
                        details=f"DSS responded with {e.cause_status_code} to attempt to mutate OI {self._oid} while 400 or 403 was expected; {e}",
                        query_timestamps=e.query_timestamps,
                    )

        with self.check(
            "Transition from Activated to Contingent is forbidden",
            self._pid + self._uids,
        ) as check:
            try:
                (self._current_ref, subscribers, q) = self._dss.put_op_intent(
                    oi_id=self._oid,
                    extents=flight_extents,
                    key=[],
                    ovn=self._current_ref.ovn,
                    state=OperationalIntentState.Nonconforming,
                    base_url=DUMMY_USS_BASE_URL,
                    # Force the query to use the SCD scope so the CMSA scope is not added
                    force_query_scopes=Scope.StrategicCoordination,
                )
                self.record_query(q)
                check.record_failed(
                    "Transition from Activated to Contingent was allowed using an improper scope",
                    details=f"DSS responded successfully to attempt to mutate OI {self._oid} from Activated to Contingent",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as e:
                self.record_queries(e.queries)
                if e.cause_status_code not in [400, 403]:
                    check.record_failed(
                        f"Transition from Activated to Contingent was rejected with wrong code",
                        details=f"DSS responded with {e.cause_status_code} to attempt to mutate OI {self._oid} while 400 or 403 was expected; {e}",
                        query_timestamps=e.query_timestamps,
                    )

        self.end_test_step()

        self.begin_test_step("Transition the OIR to Ended")

        with self.check(
            "Transition from Activated to Ended is allowed", self._pid
        ) as check:
            try:
                (self._current_ref, subscribers, q) = self._dss.put_op_intent(
                    oi_id=self._oid,
                    extents=flight_extents,
                    key=[],
                    ovn=self._current_ref.ovn,
                    state=OperationalIntentState.Activated,
                    base_url=DUMMY_USS_BASE_URL,
                )
                self.record_query(q)
            except QueryError as e:
                self.record_queries(e.queries)
                check.record_failed(
                    f"Transition from Activated to Ended was wrongly rejected",
                    details=f"DSS responded with {e.cause_status_code} to attempt to transition OI {self._oid}; {e}",
                    query_timestamps=e.query_timestamps,
                )

        self.end_test_step()

        self.begin_test_step(
            "Attempt transition of an ended operational intent reference to an unauthorized state"
        )

        with self.check(
            "Transition from Ended to Nonconforming is forbidden",
            self._pid + self._uids,
        ) as check:
            try:
                (self._current_ref, subscribers, q) = self._dss.put_op_intent(
                    oi_id=self._oid,
                    extents=flight_extents,
                    key=[],
                    ovn=self._current_ref.ovn,
                    state=OperationalIntentState.Nonconforming,
                    base_url=DUMMY_USS_BASE_URL,
                    # Force the query to use the SCD scope so the CMSA scope is not added
                    force_query_scopes=Scope.StrategicCoordination,
                )
                self.record_query(q)
                check.record_failed(
                    "Transition from Ended to Nonconforming was allowed",
                    details=f"DSS responded successfully to attempt to mutate OI {self._oid} from Ended to Nonconforming",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as e:
                self.record_queries(e.queries)
                if e.cause_status_code not in [400, 403]:
                    check.record_failed(
                        f"Transition from Ended to Nonconforming was rejected with wrong code",
                        details=f"DSS responded with {e.cause_status_code} to attempt to mutate OI {self._oid} while 400 or 403 was expected; {e}",
                        query_timestamps=e.query_timestamps,
                    )

        with self.check(
            "Transition from Ended to Contingent is forbidden", self._pid + self._uids
        ) as check:
            try:
                (self._current_ref, subscribers, q) = self._dss.put_op_intent(
                    oi_id=self._oid,
                    extents=flight_extents,
                    key=[],
                    ovn=self._current_ref.ovn,
                    state=OperationalIntentState.Nonconforming,
                    base_url=DUMMY_USS_BASE_URL,
                    # Force the query to use the SCD scope so the CMSA scope is not added
                    force_query_scopes=Scope.StrategicCoordination,
                )
                check.record_failed(
                    "Transition from Ended to Contingent was allowed",
                    details=f"DSS responded successfully to attempt to mutate OI {self._oid} from Ended to Contingent",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as e:
                self.record_queries(e.queries)
                if e.cause_status_code not in [400, 403]:
                    check.record_failed(
                        f"Transition from Ended to Contingent was rejected with wrong code",
                        details=f"DSS responded with {e.cause_status_code} to attempt to mutate OI {self._oid} while 400 or 403 was expected; {e}",
                        query_timestamps=e.query_timestamps,
                    )
        self.end_test_step()

    def cleanup(self):
        self.begin_cleanup()

        # We remove the op intents that were created for this scenario
        self._clean_known_op_intents_ids()

        self.end_cleanup()
