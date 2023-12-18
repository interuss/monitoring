from typing import List

from uas_standards.astm.f3548.v21 import api as f3548v21
from uas_standards.astm.f3548.v21.api import OperationalIntentState

from monitoring.monitorlib.geotemporal import Volume4DCollection
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources.astm.f3548.v21 import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstance,
    DUMMY_USS_BASE_URL,
)
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource
from monitoring.uss_qualifier.resources.flight_planning import FlightIntentsResource
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntent,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_intents_resource import (
    unpack_flight_intents,
)
from monitoring.uss_qualifier.resources.interuss import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class OpIntentReferenceAccessControl(TestScenario):
    """
    Tests that the DSS only allows a client to edit their own flight intents, but not those of another USS.
    """

    OP_INTENT_1 = register_resource_type(375, "Operational Intent Reference")
    OP_INTENT_2 = register_resource_type(376, "Operational Intent Reference")

    # The DSS under test
    _dss: DSSInstance
    _pid: List[str]

    # The same DSS, available via a separate auth adapter
    _dss_separate_creds: DSSInstance

    _flight1_planned: FlightIntent
    _flight2_planned: FlightIntent

    _volumes1: Volume4DCollection
    _volumes2: Volume4DCollection

    _intents_extent: f3548v21.Volume4D

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
        self._dss = dss.dss
        self._pid = [dss.dss.participant_id]

        self._oid_1 = id_generator.id_factory.make_id(self.OP_INTENT_1)
        self._oid_2 = id_generator.id_factory.make_id(self.OP_INTENT_2)

        if second_utm_auth is not None:
            # Build a second DSSWrapper identical to the first but with the other auth adapter
            self._dss_separate_creds = DSSInstance(
                participant_id=dss.dss.participant_id,
                base_url=dss.dss.base_url,
                has_private_address=dss.dss.has_private_address,
                auth_adapter=second_utm_auth.adapter,
            )

        try:
            (self._intents_extent, planned_flights) = unpack_flight_intents(
                flight_intents, ["flight_1", "flight_2"]
            )
            self._flight1_planned = planned_flights["flight_1"]
            self._flight2_planned = planned_flights["flight_2"]

            self._volumes1 = Volume4DCollection.from_interuss_scd_api(
                self._flight1_planned.request.operational_intent.volumes
            )

            self._volumes2 = Volume4DCollection.from_interuss_scd_api(
                self._flight2_planned.request.operational_intent.volumes
            )

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
        self.begin_test_case("Setup")

        self.begin_test_step("Ensure clean workspace")
        ws_is_clean = self._ensure_clean_workspace()
        self.end_test_step()

        if ws_is_clean:
            self.begin_test_step(
                "Create operational intent references with different credentials"
            )
            self._create_op_intents()
            self._ensure_credentials_are_different()
            self.end_test_step()

            self.end_test_case()

            self.begin_test_case(
                "Attempt unauthorized operational intent reference modification"
            )
            self.begin_test_step(
                "Attempt unauthorized operational intent reference modification"
            )

            self._check_mutation_on_non_owned_intent_fails()

            self.end_test_step()
            self.end_test_case()
        else:
            self.record_note(
                "clean_workspace",
                "Could not clean up workspace, skipping scenario",
            )

        self.end_test_scenario()

    def _clean_known_op_intents_ids(self):
        (oi_ref, q) = self._dss.get_op_intent_reference(self._oid_1)
        self.record_query(q)
        with self.check(
            "Operational intent references can be queried directly by their ID",
            self._pid,
        ) as check:
            # If the Op Intent does not exist, it's fine to run into a 404.
            if q.response.status_code not in [200, 404]:
                check.record_failed(
                    f"Could not access operational intent using main credentials",
                    details=f"DSS responded with {q.response.status_code} to attempt to access OI {self._oid_1}",
                    query_timestamps=[q.request.timestamp],
                )
        if q.response.status_code != 404:
            (_, notifs, dq) = self._dss.delete_op_intent(self._oid_1, oi_ref.ovn)
            self.record_query(dq)
            if dq.response.status_code != 200:
                with self.check(
                    "Operational intent references can be deleted by their owner",
                    self._pid,
                ) as check:
                    check.record_failed(
                        f"Could not delete operational intent using main credentials",
                        details=f"DSS responded with {dq.response.status_code} to attempt to delete OI {self._oid_1}",
                        query_timestamps=[dq.request.timestamp],
                    )

        (oi_ref, q) = self._dss_separate_creds.get_op_intent_reference(self._oid_2)
        self.record_query(q)
        with self.check(
            "Operational intent references can be queried directly by their ID",
            self._pid,
        ) as check:
            if q.response.status_code not in [200, 404]:
                check.record_failed(
                    f"Could not access operational intent using second credentials",
                    details=f"DSS responded with {q.response.status_code} to attempt to access OI {self._oid_2}",
                    query_timestamps=[q.request.timestamp],
                )
        if q.response.status_code != 404:
            (_, notifs, dq) = self._dss_separate_creds.delete_op_intent(
                self._oid_2, oi_ref.ovn
            )
            self.record_query(dq)
            with self.check(
                "Operational intent references can be deleted by their owner", self._pid
            ) as check:
                if dq.response.status_code != 200:
                    check.record_failed(
                        f"Could not delete operational intent using second credentials",
                        details=f"DSS responded with {dq.response.status_code} to attempt to delete OI {self._oid_2}",
                        query_timestamps=[dq.request.timestamp],
                    )

    def _attempt_to_delete_remaining_op_intents(self):
        """Search for op intents and attempt to delete them using the main credentials"""
        # Also check for any potential other op_intents and delete them
        (op_intents_1, q) = self._dss.find_op_intent(self._intents_extent)
        self.record_query(q)
        with self.check(
            "Operational intent references can be searched using valid credentials",
            self._pid,
        ) as check:
            if q.response.status_code != 200:
                check.record_failed(
                    f"Could not search operational intent references using main credentials",
                    details=f"DSS responded with {q.response.status_code} to attempt to search OIs",
                    query_timestamps=[q.request.timestamp],
                )

        for op_intent in op_intents_1:
            # We look for an op_intent where the uss_qualifier is the manager;
            if op_intent.manager == self._dss.client.auth_adapter.get_sub():
                (_, _, dq) = self._dss.delete_op_intent(op_intent.id, op_intent.ovn)
                self.record_query(dq)
                with self.check(
                    "Operational intent references can be deleted by their owner",
                    self._pid,
                ) as check:
                    if dq.response.status_code != 200:
                        check.record_failed(
                            f"Could not delete operational intent using main credentials",
                            details=f"DSS responded with {dq.response.status_code} to attempt to delete OI {op_intent.id}",
                            query_timestamps=[dq.request.timestamp],
                        )

        (op_intents_2, q) = self._dss_separate_creds.find_op_intent(
            self._intents_extent
        )
        self.record_query(q)
        with self.check(
            "Operational intent references can be searched using valid credentials",
            self._pid,
        ) as check:
            if q.response.status_code != 200:
                check.record_failed(
                    f"Could not search operational intent references using second credentials",
                    details=f"DSS responded with {q.response.status_code} to attempt to search OIs",
                    query_timestamps=[q.request.timestamp],
                )

        for op_intent in op_intents_2:
            # We look for an op_intent where the uss_qualifier is the manager;
            if (
                op_intent.manager
                == self._dss_separate_creds.client.auth_adapter.get_sub()
            ):
                (_, _, dq) = self._dss_separate_creds.delete_op_intent(
                    op_intent.id, op_intent.ovn
                )
                self.record_query(dq)
                with self.check(
                    "Operational intent references can be deleted by their owner",
                    self._pid,
                ) as check:
                    if dq.response.status_code != 200:
                        check.record_failed(
                            f"Could not delete operational intent using second credentials",
                            details=f"DSS responded with {dq.response.status_code} to attempt to delete OI {op_intent.id}",
                            query_timestamps=[dq.request.timestamp],
                        )

    def _ensure_clean_workspace(self) -> bool:
        """
        Tries to provide a clean workspace. If it fails to do so and the underlying check
        has a severity below HIGH, this function will return false.

        It will only return true if the workspace is clean.
        """
        # Record the subscription to help with troubleshooting in case of failures to clean-up
        self.record_note("main_credentials", self._dss.client.auth_adapter.get_sub())
        self.record_note(
            "secondary_credentials",
            self._dss_separate_creds.client.auth_adapter.get_sub(),
        )
        # Delete what we know about
        self._clean_known_op_intents_ids()
        # Search and attempt deleting what may be found through search
        self._attempt_to_delete_remaining_op_intents()

        # We can't delete anything that would be left.
        (stray_oir, q) = self._dss.find_op_intent(self._intents_extent)
        self.record_query(q)
        with self.check(
            "Operational intent references can be searched using valid credentials",
            self._pid,
        ) as check:
            if q.response.status_code != 200:
                check.record_failed(
                    f"Could not search operational intent references using main credentials",
                    details=f"DSS responded with {q.response.status_code} to attempt to search OIs",
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

    def _create_op_intents(self):
        (self._current_ref_1, subscribers1, q1) = self._dss.put_op_intent(
            id=self._oid_1,
            extents=self._volumes1.to_f3548v21(),
            key=[],
            state=OperationalIntentState.Accepted,
            base_url=DUMMY_USS_BASE_URL,
        )
        self.record_query(q1)

        with self.check(
            "Can create an operational intent with valid credentials", self._pid
        ) as check:
            if q1.response.status_code != 201:
                check.record_failed(
                    f"Could not create operational intent using main credentials",
                    details=f"DSS responded with {q1.response.status_code} to attempt to create OI {self._oid_1}",
                    query_timestamps=[q1.request.timestamp],
                )

        (
            self._current_ref_2,
            subscribers2,
            q2,
        ) = self._dss_separate_creds.put_op_intent(
            id=self._oid_2,
            extents=self._volumes2.to_f3548v21(),
            key=[self._current_ref_1.ovn],
            state=OperationalIntentState.Accepted,
            base_url=DUMMY_USS_BASE_URL,
        )
        self.record_query(q2)
        with self.check(
            "Can create an operational intent with valid credentials", self._pid
        ) as check:
            if q2.response.status_code != 201:
                check.record_failed(
                    f"Could not create operational intent using second credentials",
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
                    f"Second set of credentials is not different from the first",
                    details=f"The same credentials were provided for the main 'dss' and the additional 'second_utm_auth'"
                    f" resources ({self._dss.client.auth_adapter.get_sub()}),",
                )

    def _check_mutation_on_non_owned_intent_fails(self):
        # Attempt to update the state of the intent created with the main credentials using the second credentials
        (ref, notif, q) = self._dss_separate_creds.put_op_intent(
            id=self._oid_1,
            extents=self._volumes1.to_f3548v21(),
            key=[self._current_ref_2.ovn],
            state=OperationalIntentState.Accepted,
            base_url=self._current_ref_1.uss_base_url,
            ovn=self._current_ref_1.ovn,
        )
        self.record_query(q)
        with self.check(
            "Non-owning credentials cannot modify operational intent",
            self._pid,
        ) as check:
            if q.response.status_code != 403:
                check.record_failed(
                    f"Could update operational intent using second credentials",
                    details=f"DSS responded with {q.response.status_code} to attempt to update OI {self._oid_1}",
                    query_timestamps=[q.request.timestamp],
                )
        # Attempt to update the base_url of the intent created with the main credentials using the second credentials
        (ref, notif, q) = self._dss_separate_creds.put_op_intent(
            id=self._oid_1,
            extents=self._volumes1.to_f3548v21(),
            key=[self._current_ref_2.ovn],
            state=self._current_ref_1.state,
            base_url="https://another-url.uss/down",
            ovn=self._current_ref_1.ovn,
        )
        self.record_query(q)
        with self.check(
            "Non-owning credentials cannot modify operational intent",
            self._pid,
        ) as check:
            if q.response.status_code != 403:
                check.record_failed(
                    f"Could update operational intent using second credentials",
                    details=f"DSS responded with {q.response.status_code} to attempt to update OI {self._oid_1}",
                    query_timestamps=[q.request.timestamp],
                )

        # Try to delete
        (_, _, dq) = self._dss_separate_creds.delete_op_intent(
            self._oid_1, self._current_ref_1.ovn
        )
        self.record_query(dq)
        with self.check(
            "Non-owning credentials cannot delete operational intent",
            self._pid,
        ) as check:
            if dq.response.status_code != 403:
                check.record_failed(
                    f"Could delete operational intent using second credentials",
                    details=f"DSS responded with {dq.response.status_code} to attempt to delete OI {self._oid_1}",
                    query_timestamps=[dq.request.timestamp],
                )

        # Query again to confirm that the op intent has not been modified in any way:
        (op_1_current, qcheck) = self._dss.get_op_intent_reference(self._oid_1)
        self.record_query(qcheck)

        with self.check(
            "Operational intent references can be queried directly by their ID",
            self._pid,
        ) as check:
            if qcheck.response.status_code != 200:
                check.record_failed(
                    f"Could not access operational intent using main credentials",
                    details=f"DSS responded with {qcheck.response.status_code} to attempt to access OI {self._oid_1} "
                    f"while this OI should have been available.",
                    query_timestamps=[qcheck.request.timestamp],
                )

        with self.check(
            "Non-owning credentials cannot modify operational intent",
            self._pid,
        ) as check:
            if op_1_current != self._current_ref_1:
                check.record_failed(
                    f"Could update operational intent using second credentials",
                    details=f"Operational intent {self._oid_1} was modified by second credentials",
                    query_timestamps=[q.request.timestamp, qcheck.request.timestamp],
                )

    def cleanup(self):
        self.begin_cleanup()

        # We remove the op intents that were created for this scenario
        self._clean_known_op_intents_ids()

        self.end_cleanup()
