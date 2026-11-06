from typing import cast

from uas_standards.astm.f3548.v21.api import UssAvailabilityState
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import QueryError
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstance,
    DSSInstanceResource,
)
from monitoring.uss_qualifier.resources.communications import ClientIdentityResource
from monitoring.uss_qualifier.resources.interuss.shared_asset_coordination import (
    SharedAssetAcquisitionError,
    SharedAssetCoordinatorResource,
    SharedAssetIdentifier,
    SharedAssetType,
)
from monitoring.uss_qualifier.scenarios.astm.utm.dss.test_step_fragments import (
    get_uss_availability,
    set_uss_availability,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class UssAvailabilityMutation(TestScenario):
    """
    A scenario that verifies that USS availability status cannot be updated with the incorrect version.
    """

    _dss: DSSInstance
    _pid: list[str]

    _uss_id: str
    _shared_asset_coordinator: SharedAssetCoordinatorResource | None

    def __init__(
        self,
        dss: DSSInstanceResource,
        client_identity: ClientIdentityResource,
        shared_asset_coordinator: SharedAssetCoordinatorResource | None = None,
    ):
        """
        Args:
            dss: dss to test
            client_identity: tells us the identity we should expect as an entity's manager
            shared_asset_coordinator: coordinates exclusive access to DSS availability
        """
        super().__init__()
        self._shared_asset_coordinator = shared_asset_coordinator
        scopes: dict[str, str] = {
            Scope.AvailabilityArbitration: "read and set availability for a USS"
        }

        self._dss = dss.get_instance(scopes)
        self._pid = [self._dss.participant_id]

        self._uss_id = client_identity.subject()

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.begin_test_case("Setup")
        self._acquire_dss_availability()
        self.end_test_case()

        self.begin_test_case("Update USS availability state")
        self._step_declare_uss_available()
        self.end_test_case()

        self.begin_test_case("Update requires correct version")
        self._step_attempt_update_missing_version()
        self._step_attempt_update_incorrect_version()
        self.end_test_case()

        self.begin_test_case("Update requires valid availability")
        self._step_attempt_update_invalid_availability()
        self.end_test_case()

    def _acquire_dss_availability(self) -> None:
        if self._shared_asset_coordinator is None:
            return

        self.begin_test_step("Acquire exclusive DSS availability access")
        with self.check("DSS availability access acquired", []) as check:
            try:
                self._shared_asset_coordinator.acquire(
                    SharedAssetIdentifier(asset_type=SharedAssetType.DSSAvailability),
                    self,
                )
            except SharedAssetAcquisitionError as e:
                check.record_failed(
                    summary="Unable to acquire exclusive DSS availability access",
                    details=str(e),
                )
        self.end_test_step()

    def _step_declare_uss_available(self):
        self.begin_test_step("Declare USS as available at DSS")
        _, version = get_uss_availability(
            self,
            self._dss,
            self._uss_id,
            Scope.AvailabilityArbitration,
        )
        self._version = set_uss_availability(
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
                    details=f"Was expecting an HTTP 400, 404 or 409 response because of an missing version, but got {q.status_code}",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as qe:
                self.record_queries(qe.queries)
                # An empty version can be seen as:
                # an incorrect parameter (400), a reference to a non-existing entity (404) as well as a conflict (409)
                if qe.cause_status_code not in [400, 404, 409]:
                    check.record_failed(
                        summary="Set USS availability with missing version failed for unexpected reason",
                        details=f"Was expecting an HTTP 400, 404 or 409 response because of an missing version, but got {qe.cause_status_code}: {qe.msg}",
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
                    details=f"Was expecting an HTTP 409 response because of an incorrect version, but got {q.status_code}",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as qe:
                self.record_queries(qe.queries)
                # The spec explicitly requests a 409 response code for incorrect version.
                if qe.cause_status_code != 409:
                    check.record_failed(
                        summary="Set USS availability with incorrect version failed for unexpected reason",
                        details=f"Was expecting an HTTP 409 response because of an incorrect version, but got {qe.cause_status_code}: {qe.msg}",
                        query_timestamps=qe.query_timestamps,
                    )
        self.end_test_step()

    def _step_attempt_update_invalid_availability(self):
        self.begin_test_step("Attempt update with invalid availability")
        with self.check(
            "Request to update USS availability status with invalid availability fails",
            self._pid,
        ) as check:
            try:
                _, q = self._dss.set_uss_availability(
                    self._uss_id,
                    cast(UssAvailabilityState, "pUrPlE"),
                    self._version,
                )
                self.record_query(q)
                check.record_failed(
                    summary="Set USS availability with invalid availability was not expected to succeed",
                    details=f"Was expecting an HTTP 400 response because of an invalid availability, but got {q.status_code}",
                    query_timestamps=[q.request.timestamp],
                )
            except QueryError as qe:
                self.record_queries(qe.queries)
                if qe.cause_status_code != 400:
                    check.record_failed(
                        summary="Set USS availability with invalid availability failed for unexpected reason",
                        details=f"Was expecting an HTTP 400 response because of an invalid availability, but got {qe.cause_status_code}: {qe.msg}",
                        query_timestamps=qe.query_timestamps,
                    )
        self.end_test_step()
