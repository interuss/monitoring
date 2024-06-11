from datetime import datetime, timedelta
from typing import List, Optional

from uas_standards.astm.f3548.v21.api import (
    EntityID,
    PutConstraintReferenceParameters,
    ConstraintReference,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources.astm.f3548.v21 import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstanceResource,
    DSSInstancesResource,
    DSSInstance,
)
from monitoring.uss_qualifier.resources.communications import ClientIdentityResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.astm.utm.dss.validators.cr_validator import (
    ConstraintReferenceValidator,
)
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
    ScenarioCannotContinueError,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class CRSynchronization(TestScenario):
    """
    A scenario that checks if multiple DSS instances properly synchronize
    constraint references.

    Not in the scope of the first version of this:
     - access rights (making sure only the manager of the OIR can mutate it)
     - control of the area synchronization (by doing area searches against the secondaries)
     - mutation of an entity on a secondary DSS when it was created on the primary
     - deletion of an entity on a secondary DSS when it was created on the primary
    """

    SUB_TYPE = register_resource_type(
        390, "Operational Intent Reference for synchronization checks"
    )

    _dss: DSSInstance

    _secondary_dss_instances: List[DSSInstance]

    # Base identifier for the OIR that will be created
    _cr_id: EntityID

    # Base parameters used for OIR creation
    _cr_params: PutConstraintReferenceParameters

    # Keep track of the current OIR state
    _current_cr: Optional[ConstraintReference]

    _expected_manager: str

    def __init__(
        self,
        dss: DSSInstanceResource,
        other_instances: DSSInstancesResource,
        id_generator: IDGeneratorResource,
        client_identity: ClientIdentityResource,
        planning_area: PlanningAreaResource,
    ):
        """
        Args:
            dss: dss to test
            other_instances: dss instances to be checked for proper synchronization
            id_generator: will let us generate specific identifiers
            client_identity: tells us the identity we should expect as an entity's manager
            planning_area: An Area to use for the tests. It should be an area for which the DSS is responsible,
                 but has no other requirements.

        """
        super().__init__()
        scopes_primary = {
            Scope.StrategicCoordination: "cleanup leftover subscriptions and operational intent references",
            Scope.ConstraintManagement: "create and delete constraint references",
        }
        scopes_secondaries = {
            Scope.ConstraintManagement: "read, mutate and delete constraint references"
        }

        self._dss = dss.get_instance(scopes_primary)
        self._primary_pid = self._dss.participant_id

        self._secondary_dss_instances = [
            sec_dss.get_instance(scopes_secondaries)
            for sec_dss in other_instances.dss_instances
        ]

        self._cr_id = id_generator.id_factory.make_id(self.SUB_TYPE)
        self._expected_manager = client_identity.subject()
        self._planning_area = planning_area.specification

        # Build a ready-to-use 4D volume with no specified time for searching
        # the currently active CRs
        self._planning_area_volume4d = Volume4D(
            volume=self._planning_area.volume,
        )

    def run(self, context: ExecutionContext):

        # Check that we actually have at least one other DSS to test against:
        if not self._secondary_dss_instances:
            raise ScenarioCannotContinueError(
                "Cannot run CRSynchronization scenario: no other DSS instances to test against"
            )

        self.begin_test_scenario(context)
        self._setup_case()
        self.begin_test_case("CR synchronization")

        self.begin_test_step("Create CR validation")
        self._create_cr_with_params(self._cr_params)
        self.end_test_step()

        # Other steps to follow in subsequent PRs

        self.end_test_case()
        self.end_test_scenario()

    def _setup_case(self):
        self.begin_test_case("Setup")
        # Multiple runs of the scenario seem to rely on the same instance of it:
        # thus we need to reset the state of the scenario before running it.
        self._current_cr = None
        # We need times that are close to 'now': the params are set
        # at the beginning of each scenario run.
        self._cr_params = self._planning_area.get_new_constraint_ref_params(
            time_start=datetime.now() - timedelta(seconds=10),
            time_end=datetime.now() + timedelta(minutes=20),
        )
        self.begin_test_step("Ensure clean workspace")
        self._ensure_clean_workspace_step()
        self.end_test_step()
        self.end_test_case()

    def _ensure_clean_workspace_step(self):

        # Delete any active CRs we might own
        test_step_fragments.cleanup_active_constraint_refs(
            self,
            self._dss,
            self._planning_area_volume4d.to_f3548v21(),
            self._expected_manager,
        )

        # Make sure the OIR ID we are going to use is available
        test_step_fragments.cleanup_constraint_ref(self, self._dss, self._cr_id)
        # Drop any active subs we might own and that could interfere
        test_step_fragments.cleanup_active_subs(
            self, self._dss, self._planning_area_volume4d.to_f3548v21()
        )

    def _create_cr_with_params(self, creation_params: PutConstraintReferenceParameters):

        with self.check(
            "Create constraint reference query succeeds", [self._primary_pid]
        ) as check:
            try:
                cr, subs, q = self._dss.put_constraint_ref(
                    cr_id=self._cr_id,
                    extents=creation_params.extents,
                    uss_base_url=creation_params.uss_base_url,
                    ovn=None,
                )
                self.record_query(q)
            except QueryError as qe:
                self.record_queries(qe.queries)
                check.record_failed(
                    summary="Create constraint reference failed",
                    details=qe.msg,
                    query_timestamps=qe.query_timestamps,
                )
                return

        with self.check(
            "Create constraint reference response content is correct",
            [self._primary_pid],
        ) as check:
            ConstraintReferenceValidator(
                main_check=check,
                scenario=self,
                expected_manager=self._expected_manager,
                participant_id=[self._primary_pid],
                cr_params=creation_params,
            ).validate_created_cr(self._cr_id, new_cr=q)

        self._current_cr = cr

    def cleanup(self):
        self.begin_cleanup()
        self._ensure_clean_workspace_step()
        self.end_cleanup()
