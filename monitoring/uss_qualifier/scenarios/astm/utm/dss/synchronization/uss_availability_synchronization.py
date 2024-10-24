from typing import List, Optional

from uas_standards.astm.f3548.v21.api import (
    UssAvailabilityState,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import QueryError
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstanceResource,
    DSSInstancesResource,
    DSSInstance,
)
from monitoring.uss_qualifier.resources.communications import ClientIdentityResource
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class USSAvailabilitySynchronization(TestScenario):
    """
    A scenario that checks if multiple DSS instances properly synchronize
    the availability of a USS.

    Note that the API does not allow clients to differentiate between an unknown USS (ie,
    one for which no availability information has been set) and a USS explicitly set to the Unknown state.

    As the API does not allow clients to 'remove' availability information, this scenario
    will always attempt to leave the availability for the USS being used in an 'Unknown' state.
    """

    _dss: DSSInstance

    _dss_read_instances: List[DSSInstance]

    _uss_id: str

    _current_version: Optional[str] = None

    def __init__(
        self,
        dss: DSSInstanceResource,
        other_instances: DSSInstancesResource,
        client_identity: ClientIdentityResource,
    ):
        """
        Args:
            dss: dss to test
            other_instances: dss instances to be checked for proper synchronization
            client_identity: tells us the identity we should expect as an entity's manager
        """
        super().__init__()
        scopes_primary = {
            Scope.AvailabilityArbitration: "Set and read USS availability states"
        }
        scopes_read = {Scope.StrategicCoordination: "read USS availability states"}

        self._dss = dss.get_instance(scopes_primary)
        self._primary_pid = self._dss.participant_id

        self._dss_read_instances = [
            sec_dss.get_instance(scopes_read)
            for sec_dss in other_instances.dss_instances
        ]

        self._uss_id = client_identity.subject()

    def run(self, context: ExecutionContext):
        self._current_version = None

        self.begin_test_scenario(context)

        self.begin_test_case("Setup")
        self.begin_test_step("Ensure test USS has Unknown availability")
        self._ensure_test_uss_availability_unknown()
        self.end_test_step()
        self.end_test_case()

        self.begin_test_case("USS Availability synchronization")
        self.begin_test_step("Update USS availability on primary DSS to Normal")
        self._step_update_to_normal()
        self.end_test_step()

        self.begin_test_step("Check Normal USS availability broadcast")
        self._query_and_expect_on_secondaries(
            self._uss_id, UssAvailabilityState.Normal, self._current_version
        )
        self.end_test_step()

        self.begin_test_step("Update USS Availability on primary DSS to Down")
        self._step_update_to_down()
        self.end_test_step()

        self.begin_test_step("Check Down USS availability broadcast")
        self._query_and_expect_on_secondaries(
            self._uss_id, UssAvailabilityState.Down, self._current_version
        )
        self.end_test_step()

        self.begin_test_step("Update USS availability on primary DSS to Unknown")
        self._step_update_to_unknown()
        self.end_test_step()

        self.begin_test_step("Check Unknown USS availability broadcast")
        self._query_and_expect_on_secondaries(
            self._uss_id, UssAvailabilityState.Unknown, self._current_version
        )
        self.end_test_step()

        self.end_test_case()

        self.begin_test_case("Unknown USS state is reported as Unknown")
        self.begin_test_step("Query all DSS instances with an unknown USS identifier")
        self._step_unknown_uss_reported_as_unknown()
        self.end_test_step()

        self.end_test_case()

    def _step_unknown_uss_reported_as_unknown(self):
        unknown_uss_id = "ThisIdShouldNotExistOnTheDSS"
        with self.check(
            "Main DSS instance reports Unknown availability", self._dss.participant_id
        ) as check:
            try:
                availability, q = self._dss.get_uss_availability(
                    unknown_uss_id, scope=Scope.AvailabilityArbitration
                )
                self.record_query(q)
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Failed to get USS availability",
                    details=qe.msg,
                    query_timestamps=qe.query_timestamps,
                )
                return

        with self.check(
            "Availability version for an unknown USS should be empty",
            self._dss.participant_id,
        ) as check:
            if availability.version:
                check.record_failed(
                    summary="Availability version for an unknown USS should be empty",
                    details=f"Got version {availability.version}",
                )

        self._query_and_expect_on_secondaries(
            unknown_uss_id, UssAvailabilityState.Unknown, availability.version
        )

    def _step_update_to_unknown(self):
        with self.check(
            "USS Availability can be updated", self._dss.participant_id
        ) as check:
            try:
                self._current_version, q = self._dss.set_uss_availability(
                    self._uss_id, None, self._current_version
                )
                self.record_query(q)
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Failed to set USS availability to Unknown",
                    details=qe.msg,
                    query_timestamps=qe.query_timestamps,
                )

    def _step_update_to_down(self):
        with self.check(
            "USS Availability can be updated", self._dss.participant_id
        ) as check:
            try:
                self._current_version, q = self._dss.set_uss_availability(
                    self._uss_id, False, self._current_version
                )
                self.record_query(q)
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Failed to set USS availability to Down",
                    details=qe.msg,
                    query_timestamps=qe.query_timestamps,
                )

    def _step_update_to_normal(self):
        with self.check(
            "USS Availability can be updated", self._dss.participant_id
        ) as check:
            try:
                self._current_version, q = self._dss.set_uss_availability(
                    self._uss_id, True, self._current_version
                )
                self.record_query(q)
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Failed to set USS availability to Normal",
                    details=qe.msg,
                    query_timestamps=qe.query_timestamps,
                )

    def _ensure_test_uss_availability_unknown(self, check_consistency: bool = True):
        """
        Ensure that the availability of the USS being used for the test is set to 'Unknown',
        the default state for USS availability when nothing else is known.
        We want to both start and end this scenario with this state.
        """

        with self.check(
            "USS Availability can be requested", self._dss.participant_id
        ) as check:
            try:
                availability, q = self._dss.get_uss_availability(
                    self._uss_id, Scope.AvailabilityArbitration
                )
                self.record_query(q)
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Failed to get USS availability",
                    details=qe.msg,
                    query_timestamps=qe.query_timestamps,
                )
                return

        self._current_version = availability.version

        # If the state is not currently unknown, we set it to unknown
        if availability.status.availability != UssAvailabilityState.Unknown:
            with self.check("USS Availability can be set to Unknown") as check:
                try:
                    self._current_version, q = self._dss.set_uss_availability(
                        self._uss_id, None, self._current_version
                    )
                    self.record_query(q)
                except QueryError as qe:
                    self.record_queries(qe.queries)
                    check.record_failed(
                        summary="Failed to set USS availability to Unknown",
                        details=qe.msg,
                        query_timestamps=qe.query_timestamps,
                    )

        if not check_consistency:
            return

        self._query_and_expect_on_secondaries(
            self._uss_id, UssAvailabilityState.Unknown, self._current_version
        )

    def _query_and_expect_on_secondary(
        self,
        dss: DSSInstance,
        participants: list[str],
        uss_id: str,
        expected_availability: UssAvailabilityState,
        expected_version: str,
    ):
        with self.check(
            "USS Availability can be requested", dss.participant_id
        ) as check:
            try:
                availability, q = dss.get_uss_availability(
                    uss_id, Scope.StrategicCoordination
                )
                self.record_query(q)
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Failed to get USS availability",
                    details=qe.msg,
                    query_timestamps=qe.query_timestamps,
                )
                return

        with self.check(
            "USS Availability is consistent across every DSS instance", participants
        ) as check:
            if availability.status.availability != expected_availability:
                check.record_failed(
                    summary="USS availability not as expected on secondary DSS",
                    details=f"Expected {expected_availability}, got {availability.status.availability}",
                )

        with self.check(
            "USS Availability version is consistent across every DSS instance",
            participants,
        ) as check:
            if availability.version != expected_version:
                check.record_failed(
                    summary="USS availability version not as expected on secondary DSS",
                    details=f"Expected {expected_version}, got {availability.version}",
                )

    def _query_and_expect_on_secondaries(
        self,
        uss_id: str,
        expected_availability: UssAvailabilityState,
        expected_version: str,
    ):
        """
        Query the availability of the USS on all secondary DSS instances and check that it matches the expected availability.
        """
        for secondary_dss in self._dss_read_instances:
            self._query_and_expect_on_secondary(
                secondary_dss,
                [self._dss.participant_id, secondary_dss.participant_id],
                uss_id,
                expected_availability,
                expected_version,
            )

    def cleanup(self):
        self.begin_cleanup()
        self._ensure_test_uss_availability_unknown(check_consistency=False)
        self.end_cleanup()
