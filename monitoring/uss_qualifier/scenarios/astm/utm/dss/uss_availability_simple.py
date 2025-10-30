from uas_standards.astm.f3548.v21.api import UssAvailabilityState
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import QueryError
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstance,
    DSSInstanceResource,
)
from monitoring.uss_qualifier.resources.communications import ClientIdentityResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss.test_step_fragments import (
    get_uss_availability,
    set_uss_availability,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class UssAvailabilitySimple(TestScenario):
    """
    A scenario that verifies that USS availability status cannot be updated with the incorrect version.
    """

    _dss: DSSInstance

    _uss_id: str

    def __init__(
        self,
        dss: DSSInstanceResource,
        client_identity: ClientIdentityResource,
    ):
        """
        Args:
            dss: dss to test
            id_generator: will let us generate specific identifiers
            client_identity: tells us the identity we should expect as an entity's manager
        """
        super().__init__()
        scopes: dict[str, str] = {
            Scope.AvailabilityArbitration: "read and set availability for a USS"
        }

        self._dss = dss.get_instance(scopes)
        self._pid = [self._dss.participant_id]

        self._uss_id = client_identity.subject()

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.begin_test_case("Update USS availability state")
        self._step_declare_uss_available()
        self.end_test_case()

        self.begin_test_case("Update requires correct version")
        self._step_attempt_update_missing_version()
        self._step_attempt_update_incorrect_version()
        self.end_test_case()

    def _step_declare_uss_available(self):
        self.begin_test_step("Declare USS as available at DSS")
        _, version = get_uss_availability(
            self,
            self._dss,
            self._uss_id,
            Scope.AvailabilityArbitration,
        )
        set_uss_availability(
            self, self._dss, self._uss_id, UssAvailabilityState.Normal, version
        )
        self.end_test_step()

    def _step_attempt_update_missing_version(self):
        self.begin_test_step("Attempt update with missing version")
        with self.check(
            "Request to update USS availability status with empty version fails",
            self._pid,
        ) as check:
            try:
                _, q = self._dss.set_uss_availability(
                    self._uss_id,
                    UssAvailabilityState.Down,
                    "",
                )
                self.record_query(q)
                # We don't expect the reach this point:
                check.record_failed(
                    summary="Set USS availability with missing version was not expected to succeed",
                    details=f"Was expecting an HTTP 409 response because of an missing version, but got {q.status_code} instead",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as qe:
                self.record_queries(qe.queries)
                if qe.cause_status_code == 409:
                    # The spec explicitly requests a 409 response code for incorrect OVNs.
                    pass
                else:
                    check.record_failed(
                        summary="Set USS availability with missing version failed for unexpected reason",
                        details=f"Was expecting an HTTP 409 response because of an missing version, but got {qe.cause_status_code} instead",
                        query_timestamps=qe.query_timestamps,
                    )
        self.end_test_step()

    def _step_attempt_update_incorrect_version(self):
        self.begin_test_step("Attempt update with incorrect version")
        with self.check(
            "Request to update USS availability status with incorrect version fails",
            self._pid,
        ) as check:
            try:
                _, q = self._dss.set_uss_availability(
                    self._uss_id,
                    UssAvailabilityState.Down,
                    "ThisIsAnIncorrectVersion",
                )
                self.record_query(q)
                # We don't expect the reach this point:
                check.record_failed(
                    summary="Set USS availability with incorrect version was not expected to succeed",
                    details=f"Was expecting an HTTP 409 response because of an incorrect version, but got {q.status_code} instead",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as qe:
                self.record_queries(qe.queries)
                if qe.cause_status_code == 409:
                    # The spec explicitly requests a 409 response code for incorrect OVNs.
                    pass
                else:
                    check.record_failed(
                        summary="Set USS availability with incorrect version failed for unexpected reason",
                        details=f"Was expecting an HTTP 409 response because of an incorrect version, but got {qe.cause_status_code} instead",
                        query_timestamps=qe.query_timestamps,
                    )
        self.end_test_step()
