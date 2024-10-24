from typing import List

from uuid6 import uuid7, uuid6
from datetime import datetime, timedelta

from uas_standards.astm.f3548.v21.api import (
    OperationalIntentState,
    Volume4D,
    OperationalIntentReference,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import QueryError
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources.astm.f3548.v21 import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstanceResource,
)
from monitoring.uss_qualifier.resources.communications import ClientIdentityResource
from monitoring.uss_qualifier.resources.interuss import IDGeneratorResource
from monitoring.uss_qualifier.resources.resource import MissingResourceError
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext
from monitoring.monitorlib import geotemporal

OIR_TYPE = register_resource_type(
    398, "Operational Intent Reference for OVN suffix request"
)


class DSSOVNRequest(TestScenario):
    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        client_identity: ClientIdentityResource,
        planning_area: PlanningAreaResource,
    ):
        super().__init__()
        if not dss.supports_ovn_request:
            raise MissingResourceError(
                f"DSS resource with ID {dss.participant_id} does not support OVN requests",
                "dss",
            )
        self._dss = dss.get_instance(
            {
                Scope.StrategicCoordination: "create and delete operational intent references"
            }
        )

        self._oir_id = id_generator.id_factory.make_id(OIR_TYPE)
        self._planning_area = planning_area.specification
        self._expected_manager = client_identity.subject()

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self._setup_case()

        now = datetime.now()
        extents = [
            self._planning_area.get_volume4d(
                now - timedelta(seconds=10),
                now + timedelta(minutes=45),
            ).to_f3548v21()
        ]

        self.begin_test_case("Request for OIR OVN with valid suffix")

        self.begin_test_step("Create OIR with OVN suffix request")
        req_ovn_suffix = str(uuid7())
        oir = self._create_oir(extents, req_ovn_suffix)
        self._check_expected_ovn(req_ovn_suffix, oir)
        self.end_test_step()

        self.begin_test_step("Activate OIR with OVN suffix request")
        req_ovn_suffix = str(uuid7())
        self._activate_oir(extents, oir.ovn, req_ovn_suffix)
        self._check_expected_ovn(req_ovn_suffix, oir)
        self.end_test_step()

        self.end_test_case()

        self.begin_test_case("Request for OIR OVN with invalid suffix")

        self.begin_test_step(
            "Attempt to create OIR with OVN suffix request not being a UUID"
        )
        self._create_invalid_oir_attempt(extents, "abc")
        self.end_test_step()

        self.begin_test_step("Attempt to create OIR with OVN suffix request empty")
        self._create_invalid_oir_attempt(extents, "")
        self.end_test_step()

        self.begin_test_step(
            "Attempt to create OIR with OVN suffix request being a UUID but not v7"
        )
        self._create_invalid_oir_attempt(extents, str(uuid6()))
        self.end_test_step()

        self.begin_test_step(
            "Attempt to create OIR with OVN suffix request being an outdated UUIDv7"
        )
        self._create_invalid_oir_attempt(
            extents, "0192b9ff-793a-7a18-9b61-552a7ed277b3"
        )  # Wed, 23 Oct 2024 15:29:40 GMT
        self.end_test_step()

        self.end_test_case()

        self.end_test_scenario()

    def _create_oir(
        self, extents: List[Volume4D], req_ovn_suffix: str
    ) -> OperationalIntentReference:
        with self.check(
            "Create operational intent reference query succeeds",
            [self._dss.participant_id],
        ) as check:
            try:
                oir, _, q = self._dss.put_op_intent(
                    extents=extents,
                    key=[],
                    state=OperationalIntentState.Accepted,
                    base_url=self._planning_area.get_base_url(),
                    oi_id=self._oir_id,
                    ovn=None,
                    requested_ovn_suffix=req_ovn_suffix,
                )
                self.record_query(q)
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Create operational intent reference failed",
                    details=qe.msg,
                    query_timestamps=qe.query_timestamps,
                )

        return oir

    def _activate_oir(self, extents: List[Volume4D], ovn: str, req_ovn_suffix: str):
        with self.check(
            "Mutate operational intent reference query succeeds",
            [self._dss.participant_id],
        ) as check:
            try:
                oir, _, q = self._dss.put_op_intent(
                    extents=extents,
                    key=[],
                    state=OperationalIntentState.Activated,
                    base_url=self._planning_area.get_base_url(),
                    oi_id=self._oir_id,
                    ovn=ovn,
                    requested_ovn_suffix=req_ovn_suffix,
                )
                self.record_query(q)
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Mutate operational intent reference failed",
                    details=qe.msg,
                    query_timestamps=qe.query_timestamps,
                )

    def _create_invalid_oir_attempt(self, extents: List[Volume4D], req_ovn_suffix: str):
        with self.check(
            "Attempt to create OIR with invalid requested OVN suffix query rejected",
            [self._dss.participant_id],
        ) as check:
            try:
                oir, _, q = self._dss.put_op_intent(
                    extents=extents,
                    key=[],
                    state=OperationalIntentState.Accepted,
                    base_url=self._planning_area.get_base_url(),
                    oi_id=self._oir_id,
                    ovn=None,
                    requested_ovn_suffix=req_ovn_suffix,
                )
                self.record_query(q)
                check.record_failed(
                    summary="Creation of an operational intent reference with invalid requested OVN suffix succeeded",
                    details=f"OIR {oir.id} with OVN {oir.ovn} got incorrectly created with requested OVN suffix {req_ovn_suffix}",
                    query_timestamps=q.query_timestamps,
                )
            except QueryError as qe:
                self.record_queries(qe.queries)
                if qe.cause_status_code != 400:
                    check.record_failed(
                        summary="Creation of an operational intent reference with invalid requested OVN suffix failed with incorrect status code",
                        details=f"OIR {oir.id} with requested OVN suffix {req_ovn_suffix}: expected 400 but got {q.status_code}; {qe.msg}",
                        query_timestamps=qe.query_timestamps,
                    )

    def _check_expected_ovn(self, req_ovn_suffix: str, oir: OperationalIntentReference):
        with self.check(
            "DSS has set the expected OVN using the requested OVN suffix",
            [self._dss.participant_id],
        ) as check:
            expected_ovn = f"{self._oir_id}_{req_ovn_suffix}"
            if expected_ovn != oir.ovn:
                check.record_failed(
                    summary="DSS returned an invalid OVN after request for OVN suffix",
                    details=f"Requested OVN suffix {req_ovn_suffix}, expected OVN {expected_ovn} but got {oir.ovn}",
                )

    def _setup_case(self):
        self.begin_test_case("Setup")

        self.begin_test_step("Ensure clean workspace")
        vol = geotemporal.Volume4D(
            volume=self._planning_area.volume,
        ).to_f3548v21()

        test_step_fragments.cleanup_active_oirs(
            self,
            self._dss,
            vol,
            self._expected_manager,
        )

        test_step_fragments.cleanup_op_intent(self, self._dss, self._oir_id)
        test_step_fragments.cleanup_active_subs(self, self._dss, vol)

        self.end_test_step()
        self.end_test_case()

    def cleanup(self):
        self.begin_cleanup()
        test_step_fragments.cleanup_op_intent(self, self._dss, self._oir_id)
        self.end_cleanup()
