from datetime import datetime, timedelta

from monitoring.uss_qualifier.resources.astm.f3548.v21.subscription_params import (
    SubscriptionParams,
)
from uas_standards.astm.f3548.v21.constants import (
    Scope,
)

from monitoring.monitorlib.auth import InvalidTokenSignatureAuth
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.planning_area import (
    PlanningAreaResource,
)
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.astm.utm.dss.authentication.cr_api_validator import (
    ConstraintRefAuthValidator,
)
from monitoring.uss_qualifier.scenarios.astm.utm.dss.authentication.generic import (
    GenericAuthValidator,
)
from monitoring.uss_qualifier.scenarios.astm.utm.dss.authentication.oir_api_validator import (
    OperationalIntentRefAuthValidator,
)
from monitoring.uss_qualifier.scenarios.astm.utm.dss.authentication.sub_api_validator import (
    SubscriptionAuthValidator,
)
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class AuthenticationValidation(TestScenario):
    """
    A scenario that verifies that the DSS properly authenticates requests to all its endpoints,
    and properly validates the scopes of the requests depending on the action being performed.

    Note that this scenario does not verif that a DSS only allows an entity owner to mutate or delete them::
    this is covered in other scenarios.
    """

    SUB_TYPE = register_resource_type(
        380, "Subscription, Operational Entity Id, Constraint"
    )

    # Reuse the same ID for every type of entity.
    # As we are testing serially and cleaning up after each test, this should be fine.
    _test_id: str
    """Base identifier for the entities that will be created"""

    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        planning_area: PlanningAreaResource,
    ):
        """
        Args:
            dss: dss to test
            id_generator: will let us generate specific identifiers
            planning_area: An Area to use for the tests. It should be an area for which the DSS is responsible,
                 but has no other requirements.
        """
        super().__init__()
        # This is the proper scope for interactions with the DSS for subscriptions and operational intent
        # references in this scenario
        scd_scopes = {
            Scope.StrategicCoordination: "create and delete subscriptions and operational intent resources"
        }

        constraints_scopes = {
            Scope.ConstraintManagement: "Create, update, and delete constraints",
        }

        # For the 'wrong' scope for SCD endpoints, we pick anything from the available scopes that isn't the SCD or empty scope:
        available_scopes_scd = dss.get_authorized_scopes()
        available_scopes_scd.discard(Scope.StrategicCoordination)
        available_scopes_scd.discard("")

        if len(available_scopes_scd) > 0:
            # Sort the scopes to obtain a deterministic order, pick the first one
            available_scopes_scd = sorted(available_scopes_scd)
            self._wrong_scope_for_scd = available_scopes_scd[0]
            scd_scopes[
                self._wrong_scope_for_scd
            ] = "Attempt to query subscriptions and OIRs with wrong scope"
        else:
            self._wrong_scope_for_scd = None

        # TODO can we assume that constraint management/processing scopes will always be obtainable for a test?
        #  If not, we can easily make this part of the scenario optional.
        # For the 'wrong' scope for constraints endpoints, we pick anything from the available scopes that isn't constraint management, processing or empty scope:
        available_scopes_constraints = dss.get_authorized_scopes()
        available_scopes_constraints.discard(Scope.ConstraintManagement)
        available_scopes_constraints.discard(Scope.ConstraintProcessing)
        available_scopes_constraints.discard("")

        if len(available_scopes_constraints) > 0:
            # Sort the scopes to obtain a deterministic order, pick the first one
            available_scopes_constraints = sorted(available_scopes_constraints)
            self._wrong_scope_for_constraints = available_scopes_constraints[0]
            constraints_scopes[
                self._wrong_scope_for_constraints
            ] = "Attempt to query constraints with wrong scope"

        self._test_missing_scope = False
        if dss.can_use_scope(""):
            scd_scopes[""] = "Attempt to query subscriptions with missing scope"
            constraints_scopes[""] = "Attempt to query constraints with missing scope"
            self._test_missing_scope = True

        # Note: .get_instance should be called once we know every scope we will need,
        #  in order to guarantee that they are indeed available.
        self._scd_dss = dss.get_instance(scd_scopes)
        self._constraints_dss = dss.get_instance(constraints_scopes)

        self._pid = [self._scd_dss.participant_id]
        self._test_id = id_generator.id_factory.make_id(self.SUB_TYPE)
        self._planning_area = planning_area.specification

        # Build a ready-to-use 4D volume with no specified time for searching
        # the currently active subscriptions
        self._planning_area_volume4d = Volume4D(
            volume=self._planning_area.volume,
        )

        # Session that won't provide a token at all
        self._no_auth_session = UTMClientSession(
            self._scd_dss.base_url, auth_adapter=None
        )

        # Session that should provide a well-formed token with a wrong signature
        self._invalid_token_session = UTMClientSession(
            self._scd_dss.base_url, auth_adapter=InvalidTokenSignatureAuth()
        )

    def run(self, context: ExecutionContext):
        scd_generic_validator = GenericAuthValidator(
            self, self._scd_dss, Scope.StrategicCoordination
        )

        self.begin_test_scenario(context)
        self._setup_case()
        self.begin_test_case("Endpoint authorization")

        if self._wrong_scope_for_scd:
            self.record_note(
                "wrong_scope",
                f"Incorrect scope testing enabled with scope {self._wrong_scope_for_scd}.",
            )
        else:
            self.record_note("wrong_scope", "Incorrect scope testing disabled.")

        if self._test_missing_scope:
            self.record_note("missing_scope", "Missing scope testing enabled.")
        else:
            self.record_note("missing_scope", "Missing scope testing disabled.")

        self.begin_test_step("Subscription endpoints authentication")

        sub_validator = SubscriptionAuthValidator(
            scenario=self,
            generic_validator=scd_generic_validator,
            dss=self._scd_dss,
            test_id=self._test_id,
            planning_area=self._planning_area,
            planning_area_volume4d=self._planning_area_volume4d,
            no_auth_session=self._no_auth_session,
            invalid_token_session=self._invalid_token_session,
            test_wrong_scope=self._wrong_scope_for_scd,
            test_missing_scope=self._test_missing_scope,
        )
        sub_validator.verify_sub_endpoints_authentication()

        self.end_test_step()

        self.begin_test_step("Operational intents endpoints authentication")
        # The validator relies on the 'current' time, so it should be instantiated
        # just before being run
        oir_validator = OperationalIntentRefAuthValidator(
            scenario=self,
            generic_validator=scd_generic_validator,
            dss=self._scd_dss,
            test_id=self._test_id,
            planning_area=self._planning_area,
            planning_area_volume4d=self._planning_area_volume4d,
            no_auth_session=self._no_auth_session,
            invalid_token_session=self._invalid_token_session,
            test_wrong_scope=self._wrong_scope_for_scd,
            test_missing_scope=self._test_missing_scope,
        )
        oir_validator.verify_oir_endpoints_authentication()
        self.end_test_step()

        self.begin_test_step("Constraint reference endpoints authentication")
        cr_validator = ConstraintRefAuthValidator(
            self,
            GenericAuthValidator(
                self, self._constraints_dss, Scope.ConstraintManagement
            ),
            self._constraints_dss,
            self._test_id,
            self._planning_area,
            self._planning_area_volume4d,
            self._no_auth_session,
            self._invalid_token_session,
            self._wrong_scope_for_scd,
            self._test_missing_scope,
        )
        cr_validator.verify_cr_endpoints_authentication()
        self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def _setup_case(self):
        self.begin_test_case("Setup")

        self._ensure_clean_workspace_step()

        self.end_test_case()

    def _ensure_clean_workspace_step(self):
        self.begin_test_step("Ensure clean workspace")
        # Check for subscriptions that will collide with our IDs and drop them
        self._ensure_test_entities_dont_exist()
        # Drop any active remaining sub
        self._ensure_no_active_subs_exist()
        self.end_test_step()

    def _ensure_test_entities_dont_exist(self):

        # Drop OIR's first: subscriptions may be tied to them and can't be deleted
        # as long as they exist
        test_step_fragments.cleanup_op_intent(self, self._scd_dss, self._test_id)
        test_step_fragments.cleanup_sub(self, self._scd_dss, self._test_id)

    def _ensure_no_active_subs_exist(self):
        test_step_fragments.cleanup_active_subs(
            self,
            self._scd_dss,
            self._planning_area_volume4d,
        )

    def cleanup(self):
        self.begin_cleanup()
        self._ensure_test_entities_dont_exist()
        self.end_cleanup()
