import arrow
from uas_standards.astm.f3548.v21 import api as f3548v21
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.clients.flight_planning.flight_info import (
    AirspaceUsageState,
    UasState,
)
from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    FlightInfoTemplate,
)
from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geotemporal import Volume4D, Volume4DCollection
from monitoring.monitorlib.temporal import Time, TimeDuringTest
from monitoring.monitorlib.testing import make_fake_url
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources.astm.f3548.v21 import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource
from monitoring.uss_qualifier.resources.flight_planning import FlightIntentsResource
from monitoring.uss_qualifier.resources.flight_planning.flight_intent_validation import (
    ExpectedFlightIntent,
    validate_flight_intent_templates,
)
from monitoring.uss_qualifier.resources.interuss import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext

# A base URL for a USS that is not expected to be ever called
# Used to mimic the behavior of a USS and need to provide a base URL.
# As the area used for tests is cleared before the tests, there should be no need to have this URL be reachable.
DUMMY_USS_BASE_URL = make_fake_url()


class OpIntentReferenceAccessControl(TestScenario):
    """
    Tests that the DSS only allows a client to edit their own flight intents, but not those of another USS.
    """

    OP_INTENT_1 = register_resource_type(375, "Operational Intent Reference")
    OP_INTENT_2 = register_resource_type(376, "Operational Intent Reference")

    # The DSS under test
    _dss: DSSInstance
    _pid: list[str]

    # Participant IDs of users using this DSS instance
    _uids: list[str]

    # The same DSS, available via a separate auth adapter
    _dss_separate_creds: DSSInstance

    _flight_1: FlightInfoTemplate
    _flight_2: FlightInfoTemplate

    _current_ref_1: f3548v21.OperationalIntentReference
    _current_ref_2: f3548v21.OperationalIntentReference

    def __init__(
        self,
        flight_intents: FlightIntentsResource,
        dss: DSSInstanceResource,
        second_utm_auth: AuthAdapterResource,
        id_generator: IDGeneratorResource,
    ):
        super().__init__()
        scopes = {
            Scope.StrategicCoordination: "create and delete operational intent references"
        }
        self._dss = dss.get_instance(scopes)
        self._pid = [self._dss.participant_id]
        self._uids = self._dss.user_participant_ids

        self._oid_1 = id_generator.id_factory.make_id(self.OP_INTENT_1)
        self._oid_2 = id_generator.id_factory.make_id(self.OP_INTENT_2)

        if second_utm_auth is not None:
            # Build a second DSSWrapper identical to the first but with the other auth adapter
            self._dss_separate_creds = self._dss.with_different_auth(
                second_utm_auth, scopes
            )

        expected_flight_intents = [
            ExpectedFlightIntent(
                "flight_1",
                "Flight 1",
                must_not_conflict_with=["Flight 2"],
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
            ),
            ExpectedFlightIntent(
                "flight_2",
                "Flight 2",
                must_not_conflict_with=["Flight 1"],
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
            ),
        ]

        templates = flight_intents.get_flight_intents()
        try:
            validate_flight_intent_templates(templates, expected_flight_intents)
        except ValueError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: {e}"
            )
        self._flight_1 = templates["flight_1"]
        self._flight_2 = templates["flight_2"]

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

        if ws_is_clean:
            self.begin_test_step(
                "Create operational intent references with different credentials"
            )
            times[TimeDuringTest.TimeOfEvaluation] = Time(arrow.utcnow())
            self._create_op_intents(times)
            self._ensure_credentials_are_different()
            self.end_test_step()

            self.end_test_case()

            self.begin_test_case(
                "Attempt unauthorized operational intent reference modification"
            )
            self.begin_test_step(
                "Attempt unauthorized operational intent reference modification"
            )

            self._check_mutation_on_non_owned_intent_fails(times)

            self.end_test_step()
            self.end_test_case()
        else:
            self.record_note(
                "clean_workspace",
                "Could not clean up workspace, skipping scenario",
            )

        self.end_test_scenario()

    def _get_extents(self, times: dict[TimeDuringTest, Time]) -> Volume4D:
        extents = Volume4DCollection()
        for info in (self._flight_1.resolve(times), self._flight_2.resolve(times)):
            extents.extend(info.basic_information.area)

        return extents.bounding_volume

    def _clean_known_op_intents_ids(self):
        with self.check(
            "Operational intent references can be queried by ID",
            self._pid,
        ) as check:
            try:
                (oi_ref, q) = self._dss.get_op_intent_reference(self._oid_1)
                self.record_query(q)
            except QueryError as e:
                self.record_queries(e.queries)
                q = e.queries[0]
                # If the Op Intent does not exist, it's fine to run into a 404.
                if q.response.status_code != 404:
                    check.record_failed(
                        "Could not access operational intent using main credentials",
                        details=f"DSS responded with {q.response.status_code} to attempt to access OI {self._oid_1}; {e}",
                        query_timestamps=[q.request.timestamp],
                    )
        if q.response.status_code != 404:
            with self.check(
                "Operational intent references can be searched for",
                # TODO: This is not the appropriate check when attempting to delete an operational intent reference
                self._pid,
            ) as check:
                try:
                    (_, notifs, dq) = self._dss.delete_op_intent(
                        self._oid_1, oi_ref.ovn
                    )
                    self.record_query(dq)
                except QueryError as e:
                    self.record_queries(e.queries)
                    dq = e.queries[0]
                    check.record_failed(
                        "Could not delete operational intent using main credentials",
                        details=f"DSS responded with {dq.response.status_code} to attempt to delete OI {self._oid_1}; {e}",
                        query_timestamps=[dq.request.timestamp],
                    )

        with self.check(
            "Operational intent references can be queried by ID",
            self._pid,
        ) as check:
            try:
                (oi_ref, q) = self._dss_separate_creds.get_op_intent_reference(
                    self._oid_2
                )
                self.record_query(q)
            except QueryError as e:
                self.record_queries(e.queries)
                q = e.queries[0]
                if q.response.status_code != 404:
                    check.record_failed(
                        "Could not access operational intent using second credentials",
                        details=f"DSS responded with {q.response.status_code} to attempt to access OI {self._oid_2}; {e}",
                        query_timestamps=[q.request.timestamp],
                    )
        if q.response.status_code != 404:
            with self.check("Operational intent reference removed", self._pid) as check:
                try:
                    (_, notifs, dq) = self._dss_separate_creds.delete_op_intent(
                        self._oid_2, oi_ref.ovn
                    )
                    self.record_query(dq)
                except QueryError as e:
                    self.record_queries(e.queries)
                    dq = e.queries[0]
                    check.record_failed(
                        "Could not delete operational intent using second credentials",
                        details=f"DSS responded with {dq.response.status_code} to attempt to delete OI {self._oid_2}; {e}",
                        query_timestamps=[dq.request.timestamp],
                    )

    def _attempt_to_delete_remaining_op_intents(
        self, times: dict[TimeDuringTest, Time]
    ):
        """Search for op intents and attempt to delete them using the main credentials"""

        extent = self._get_extents(times)
        with self.check(
            "Operational intent references can be searched for",
            self._pid,
        ) as check:
            try:
                # Also check for any potential other op_intents and delete them
                (op_intents_1, q) = self._dss.find_op_intent(extent.to_f3548v21())
                self.record_query(q)
            except QueryError as e:
                self.record_queries(e.queries)
                q = e.queries[0]
                check.record_failed(
                    "Could not search operational intent references using main credentials",
                    details=f"DSS responded with {q.response.status_code} to attempt to search OIs; {e}",
                    query_timestamps=[q.request.timestamp],
                )

        for op_intent in op_intents_1:
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
                        dq = e.queries[0]
                        check.record_failed(
                            "Could not delete operational intent using main credentials",
                            details=f"DSS responded with {dq.response.status_code} to attempt to delete OI {op_intent.id}; {e}",
                            query_timestamps=[dq.request.timestamp],
                        )

        with self.check(
            "Operational intent references can be searched for",
            self._pid,
        ) as check:
            try:
                (op_intents_2, q) = self._dss_separate_creds.find_op_intent(
                    extent.to_f3548v21()
                )
                self.record_query(q)
            except QueryError as e:
                self.record_queries(e.queries)
                q = e.queries[0]
                check.record_failed(
                    "Could not search operational intent references using second credentials",
                    details=f"DSS responded with {q.response.status_code} to attempt to search OIs; {e}",
                    query_timestamps=[q.request.timestamp],
                )

        for op_intent in op_intents_2:
            # We look for an op_intent where the uss_qualifier is the manager;
            if (
                op_intent.manager
                == self._dss_separate_creds.client.auth_adapter.get_sub()
            ):
                with self.check(
                    "Operational intent reference removed",
                    self._pid,
                ) as check:
                    try:
                        (_, _, dq) = self._dss_separate_creds.delete_op_intent(
                            op_intent.id, op_intent.ovn
                        )
                        self.record_query(dq)
                    except QueryError as e:
                        self.record_queries(e.queries)
                        dq = e.queries[0]
                        check.record_failed(
                            "Could not delete operational intent using second credentials",
                            details=f"DSS responded with {dq.response.status_code} to attempt to delete OI {op_intent.id}; {e}",
                            query_timestamps=[dq.request.timestamp],
                        )

    def _ensure_clean_workspace(self, times: dict[TimeDuringTest, Time]) -> bool:
        """
        Tries to provide a clean workspace. If it fails to do so and the underlying check
        has a severity below HIGH, this function will return false.

        It will only return true if the workspace is clean.
        """
        extent = self._get_extents(times)

        # Record the subscription to help with troubleshooting in case of failures to clean-up
        self.record_note("main_credentials", self._dss.client.auth_adapter.get_sub())
        self.record_note(
            "secondary_credentials",
            self._dss_separate_creds.client.auth_adapter.get_sub(),
        )
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
                    "Could not search operational intent references using main credentials",
                    details=f"DSS responded with {q.response.status_code} to attempt to search OIs; {e}",
                    query_timestamps=[q.request.timestamp],
                )

        with self.check(
            "Any existing operational intent reference has been removed", self._pid
        ) as check:
            if len(stray_oir) > 0:
                check.record_failed(
                    "Found operational intents that cannot be cleaned up",
                    details=f"Operational intents that cannot be cleaned up were found: {stray_oir}",
                    query_timestamps=[q.request.timestamp],
                )
                return False

        return True

    def _create_op_intents(self, times: dict[TimeDuringTest, Time]):
        flight_1 = self._flight_1.resolve(times)
        with self.check(
            "Can create an operational intent with valid credentials", self._pid
        ) as check:
            try:
                (self._current_ref_1, subscribers1, q1) = self._dss.put_op_intent(
                    oi_id=self._oid_1,
                    extents=flight_1.basic_information.area.to_f3548v21(),
                    key=[],
                    state=flight_1.get_f3548v21_op_intent_state(),
                    base_url=DUMMY_USS_BASE_URL,
                )
                self.record_query(q1)
            except QueryError as e:
                self.record_queries(e.queries)
                q1 = e.queries[0]
                check.record_failed(
                    "Could not create operational intent using main credentials",
                    details=f"DSS responded with {q1.response.status_code} to attempt to create OI {self._oid_1}; {e}",
                    query_timestamps=[q1.request.timestamp],
                )

        flight_2 = self._flight_2.resolve(times)
        with self.check(
            "Can create an operational intent with valid credentials", self._pid
        ) as check:
            try:
                (
                    self._current_ref_2,
                    subscribers2,
                    q2,
                ) = self._dss_separate_creds.put_op_intent(
                    oi_id=self._oid_2,
                    extents=flight_2.basic_information.area.to_f3548v21(),
                    key=[self._current_ref_1.ovn],
                    state=flight_2.get_f3548v21_op_intent_state(),
                    base_url=DUMMY_USS_BASE_URL,
                )
                self.record_query(q2)
            except QueryError as e:
                self.record_queries(e.queries)
                q2 = e.queries[0]
                check.record_failed(
                    "Could not create operational intent using second credentials",
                    details=f"DSS responded with {q2.response.status_code} to attempt to create OI {self._oid_2}",
                    query_timestamps=[q2.request.timestamp],
                )

    def _ensure_credentials_are_different(self):
        """
        Checks the auth adapters for the subscription they used and raises an exception if they are the same.
        Note that both adapters need to have been used at least once before this check can be performed,
        otherwise they have no token available.
        """
        with self.check("Passed sets of credentials are different", self._pid) as check:
            if (
                self._dss_separate_creds.client.auth_adapter.get_sub()
                == self._dss.client.auth_adapter.get_sub()
            ):
                check.record_failed(
                    "Second set of credentials is not different from the first",
                    details=f"The same credentials were provided for the main 'dss' and the additional 'second_utm_auth'"
                    f" resources ({self._dss.client.auth_adapter.get_sub()}),",
                )

    def _check_mutation_on_non_owned_intent_fails(
        self, times: dict[TimeDuringTest, Time]
    ):
        flight_1 = self._flight_1.resolve(times)
        with self.check(
            "Non-owning credentials cannot modify operational intent",
            self._pid + self._uids,
        ) as check:
            try:
                # Attempt to update the uss_base_url of the intent created with the main credentials using the second credentials
                (ref, notif, q) = self._dss_separate_creds.put_op_intent(
                    oi_id=self._oid_1,
                    extents=flight_1.basic_information.area.to_f3548v21(),
                    key=[self._current_ref_2.ovn],
                    state=flight_1.get_f3548v21_op_intent_state(),
                    base_url=self._current_ref_1.uss_base_url + "/mutated",
                    ovn=self._current_ref_1.ovn,
                )
                self.record_query(q)
                check.record_failed(
                    "Could update operational intent using second credentials",
                    details=f"DSS responded with {q.response.status_code} to attempt to update OI {self._oid_1}",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as e:
                self.record_queries(e.queries)
                q = e.queries[0]
                if q.response.status_code != 403:
                    check.record_failed(
                        "Attempt to update operational intent using second credentials failed with an unexpected status code (expected 403)",
                        details=f"DSS responded with {q.response.status_code} to attempt to update OI {self._oid_1}; {e}",
                        query_timestamps=[q.request.timestamp],
                    )

        with self.check(
            "Non-owning credentials cannot modify operational intent",
            self._pid + self._uids,
        ) as check:
            try:
                # Attempt to update the base_url of the intent created with the main credentials using the second credentials
                (ref, notif, q) = self._dss_separate_creds.put_op_intent(
                    oi_id=self._oid_1,
                    extents=flight_1.basic_information.area.to_f3548v21(),
                    key=[self._current_ref_2.ovn],
                    state=self._current_ref_1.state,
                    base_url=make_fake_url("down"),
                    ovn=self._current_ref_1.ovn,
                )
                self.record_query(q)
                check.record_failed(
                    "Could update operational intent using second credentials",
                    details=f"DSS responded with {q.response.status_code} to attempt to update OI {self._oid_1}",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as e:
                self.record_queries(e.queries)
                q = e.queries[0]
                if q.response.status_code != 403:
                    check.record_failed(
                        "Attempt to update operational intent using second credentials failed with an unexpected status code (expected 403)",
                        details=f"DSS responded with {q.response.status_code} to attempt to update OI {self._oid_1}; {e}",
                        query_timestamps=[q.request.timestamp],
                    )

        # Try to delete
        with self.check(
            "Non-owning credentials cannot delete operational intent",
            self._pid + self._uids,
        ) as check:
            try:
                (_, _, dq) = self._dss_separate_creds.delete_op_intent(
                    self._oid_1, self._current_ref_1.ovn
                )
                self.record_query(dq)
                check.record_failed(
                    "Could delete operational intent using second credentials",
                    details=f"DSS responded with {dq.response.status_code} to attempt to delete OI {self._oid_1}",
                    query_timestamps=[dq.request.timestamp],
                )
            except QueryError as e:
                self.record_queries(e.queries)
                dq = e.queries[0]
                if dq.response.status_code != 403:
                    check.record_failed(
                        "DSS did not fail with expected status code 403",
                        details=f"DSS responded with {dq.response.status_code} to attempt to delete OI {self._oid_1}; {e}",
                        query_timestamps=[dq.request.timestamp],
                    )

        with self.check(
            "Operational intent references can be queried directly by their ID",
            self._pid,
        ) as check:
            try:
                # Query again to confirm that the op intent has not been modified in any way:
                (op_1_current, qcheck) = self._dss.get_op_intent_reference(self._oid_1)
                self.record_query(qcheck)
            except QueryError as e:
                self.record_queries(e.queries)
                qcheck = e.queries[0]
                check.record_failed(
                    "Could not access operational intent using main credentials",
                    details=f"DSS responded with {qcheck.response.status_code} to attempt to access OI {self._oid_1} "
                    f"while this OI should have been available; {e}",
                    query_timestamps=[qcheck.request.timestamp],
                )

        with self.check(
            "Non-owning credentials cannot modify operational intent",
            self._pid + self._uids,
        ) as check:
            if op_1_current != self._current_ref_1:
                check.record_failed(
                    "Could update operational intent using second credentials",
                    details=f"Operational intent {self._oid_1} was modified by second credentials",
                    query_timestamps=[q.request.timestamp, qcheck.request.timestamp],
                )

    def cleanup(self):
        self.begin_cleanup()

        # We remove the op intents that were created for this scenario
        self._clean_known_op_intents_ids()

        self.end_cleanup()
