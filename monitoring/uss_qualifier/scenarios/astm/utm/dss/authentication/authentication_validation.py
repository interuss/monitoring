from typing import Optional

from uas_standards.astm.f3548.v21.api import UssAvailabilityState
from uas_standards.astm.f3548.v21.constants import (
    Scope,
)

from monitoring.monitorlib.auth import InvalidTokenSignatureAuth
from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.monitorlib.inspection import fullname
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstanceResource,
    DSSInstance,
)
from monitoring.uss_qualifier.resources.astm.f3548.v21.planning_area import (
    PlanningAreaResource,
)
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.resources.resource import MissingResourceError
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.astm.utm.dss.authentication.availability_api_validator import (
    AvailabilityAuthValidator,
)
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

    Note that this scenario does not verif that a DSS only allows an entity owner to mutate or delete them:
    this is covered in other scenarios.
    """

    SUB_TYPE = register_resource_type(
        380, "Subscription, Operational Entity Id, Constraint"
    )

    # Reuse the same ID for every type of entity.
    # As we are testing serially and cleaning up after each test, this should be fine.
    _test_id: str
    """Base identifier for the entities that will be created"""

    _scd_dss: Optional[DSSInstance] = None
    _availability_dss: Optional[DSSInstance] = None
    _constraints_dss: Optional[DSSInstance] = None

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

        # Check if we can test SCD endpoints:
        if dss.can_use_scope(Scope.StrategicCoordination):
            scd_scopes = {
                Scope.StrategicCoordination: "create and delete subscriptions and operational intent resources"
            }
            self._wrong_scope_for_scd = dss.get_authorized_scope_not_in(
                [
                    Scope.StrategicCoordination,  # Allowed to get and update
                    # CMSA is excluded too, as it is allowed to do certain operations on the OIR endpoints
                    Scope.ConformanceMonitoringForSituationalAwareness,
                    "",  # Already Used for empty scope testing
                ]
            )

            if self._wrong_scope_for_scd is not None:
                scd_scopes[
                    self._wrong_scope_for_scd
                ] = "Attempt to query subscriptions and OIRs with wrong scope"
        else:
            scd_scopes = None
            self._wrong_scope_for_scd = None

        # Check if we can test availability endpoints:
        if dss.can_use_scope(Scope.AvailabilityArbitration):
            availability_scopes = {
                Scope.AvailabilityArbitration: "read and set availability for a USS"
            }
            self._wrong_scope_for_availability = dss.get_authorized_scope_not_in(
                [
                    Scope.AvailabilityArbitration,  # Allowed to get and update
                    Scope.ConformanceMonitoringForSituationalAwareness,  # Allowed to get
                    Scope.StrategicCoordination,  # Allowed to get
                    "",  # Already Used for empty scope testing
                ]
            )

            if self._wrong_scope_for_availability is not None:
                availability_scopes[
                    self._wrong_scope_for_availability
                ] = "Attempt to query availability with wrong scope"
        else:
            availability_scopes = None
            self._wrong_scope_for_availability = None

        if dss.can_use_scope(Scope.ConstraintManagement):
            constraints_scopes = {
                Scope.ConstraintManagement: "Create, update, and delete constraints",
            }

            self._wrong_scope_for_constraints = dss.get_authorized_scope_not_in(
                [
                    Scope.ConstraintManagement,  # Allowed to get and update
                    Scope.ConstraintProcessing,  # Allowed to get
                    "",  # Already Used for empty scope testing
                ]
            )

            if self._wrong_scope_for_constraints is not None:
                constraints_scopes[
                    self._wrong_scope_for_constraints
                ] = "Attempt to query constraints with wrong scope"
        else:
            constraints_scopes = None
            self._wrong_scope_for_constraints = None

        self._test_missing_scope = False
        if dss.can_use_scope(""):
            # Add empty scope to every map when they are non-empty:
            # (Empty means the endpoint group should not be tested at all)
            if scd_scopes:
                scd_scopes[
                    ""
                ] = "Attempt to query subscriptions and OIRs with missing scope"
            if availability_scopes:
                availability_scopes[
                    ""
                ] = "Attempt to query availability with missing scope"
            if constraints_scopes:
                constraints_scopes[
                    ""
                ] = "Attempt to query constraints with missing scope"
            self._test_missing_scope = True

        # Note: .get_instance should be called once we know every scope we will need,
        #  in order to guarantee that they are indeed available.
        # If the scopes for an endpoint group are empty, it means we're not allowed to obtain them
        # and skip .get_instance altogether (otherwise the scenario would not be run)
        if scd_scopes:
            self._scd_dss = dss.get_instance(scd_scopes)
        if constraints_scopes:
            self._constraints_dss = dss.get_instance(constraints_scopes)
        if availability_scopes:
            self._availability_dss = dss.get_instance(availability_scopes)

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

        if (
            not self._scd_dss
            and not self._constraints_dss
            and not self._availability_dss
        ):
            raise MissingResourceError(
                f"AuthAdapterResource provided to {fullname(type(self))} has none of the required scopes for this scenario.",
                "<unknown>",
            )

    def run(self, context: ExecutionContext):
        scd_generic_validator = GenericAuthValidator(
            self, self._scd_dss, Scope.StrategicCoordination
        )

        self.begin_test_scenario(context)
        self._setup_case()
        self.begin_test_case("Endpoint authorization")

        if self._test_missing_scope:
            self.record_note("missing_scope", "Missing scope testing enabled.")
        else:
            self.record_note("missing_scope", "Missing scope testing disabled.")

        if self._scd_dss:
            self.record_note(
                "scd",
                "Testing Strategic Coordination endpoints (Subscriptions and OIRs)",
            )
            self.begin_test_step("Subscription endpoints authentication")

            if self._wrong_scope_for_scd:
                self.record_note(
                    "scd_wrong_scope",
                    f"Incorrect scope testing enabled with scope {self._wrong_scope_for_scd}.",
                )
            else:
                self.record_note("scd_wrong_scope", "Incorrect scope testing disabled.")

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
        else:
            self.record_note(
                "scd",
                "Skipping Strategic Coordination endpoints (Subscriptions and OIRs)",
            )

        if self._availability_dss:
            self.record_note("availability", "Testing Availability endpoints")
            self.begin_test_step("Availability endpoints authentication")

            if self._wrong_scope_for_availability:
                self.record_note(
                    "availability_wrong_scope",
                    f"Incorrect scope testing enabled for availability endpoints with scope {self._wrong_scope_for_availability}.",
                )
            else:
                self.record_note(
                    "availability_wrong_scope",
                    "Incorrect scope testing disabled for availability endpoints",
                )

            availability_validator = AvailabilityAuthValidator(
                scenario=self,
                generic_validator=GenericAuthValidator(
                    self, self._availability_dss, Scope.AvailabilityArbitration
                ),
                dss=self._availability_dss,
                test_id=self._test_id,
                no_auth_session=self._no_auth_session,
                invalid_token_session=self._invalid_token_session,
                test_wrong_scope=self._wrong_scope_for_availability,
                test_missing_scope=self._test_missing_scope,
            )
            availability_validator.verify_availability_endpoints_authentication()
            self.end_test_step()
        else:
            self.record_note("availability", "Skipping Availability endpoints")

        if self._constraints_dss:
            self.record_note("constraints", "Testing Constraint Reference endpoints")
            self.begin_test_step("Constraint reference endpoints authentication")
            if self._wrong_scope_for_constraints:
                self.record_note(
                    "constraints_wrong_scope",
                    f"Incorrect scope testing enabled with scope {self._wrong_scope_for_constraints}.",
                )
            else:
                self.record_note(
                    "constraints_wrong_scope", "Incorrect scope testing disabled."
                )
            cr_validator = ConstraintRefAuthValidator(
                scenario=self,
                generic_validator=GenericAuthValidator(
                    self, self._constraints_dss, Scope.ConstraintManagement
                ),
                dss=self._constraints_dss,
                test_id=self._test_id,
                planning_area=self._planning_area,
                planning_area_volume4d=self._planning_area_volume4d,
                no_auth_session=self._no_auth_session,
                invalid_token_session=self._invalid_token_session,
                test_wrong_scope=self._wrong_scope_for_constraints,
                test_missing_scope=self._test_missing_scope,
            )
            cr_validator.verify_cr_endpoints_authentication()
            self.end_test_step()
        else:
            self.record_note("constraints", "Skipping Constraint Reference endpoints")

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

        # Make sure the test ID for uss availability is set to 'Unknown'
        # if we are testing availabilities
        if self._availability_dss:
            self._ensure_availability_is_unknown()

    def _ensure_no_active_subs_exist(self):
        test_step_fragments.cleanup_active_subs(
            self,
            self._scd_dss,
            self._planning_area_volume4d,
        )

    def _ensure_availability_is_unknown(self):

        with self.check("USS Availability can be requested", self._pid) as check:
            try:
                availability, q = self._availability_dss.get_uss_availability(
                    self._test_id, scope=Scope.AvailabilityArbitration
                )
                self.record_query(q)
            except QueryError as e:
                self.record_queries(e.queries)
                check.record_failed(
                    summary="Could not get USS availability",
                    details=f"Failed to get USS availability: {e}",
                    query_timestamps=[q.request.timestamp for q in e.queries],
                )

        if availability.status != UssAvailabilityState.Unknown:
            with self.check("USS Availability can be updated", self._pid) as check:
                try:
                    availability, q = self._availability_dss.set_uss_availability(
                        self._test_id, available=None, version=availability.version
                    )
                    self.record_query(q)
                except QueryError as e:
                    self.record_queries(e.queries)
                    check.record_failed(
                        summary="Could not set USS availability",
                        details=f"Failed to set USS availability: {e}",
                        query_timestamps=[q.request.timestamp for q in e.queries],
                    )

    def cleanup(self):
        self.begin_cleanup()
        self._ensure_test_entities_dont_exist()
        self.end_cleanup()
