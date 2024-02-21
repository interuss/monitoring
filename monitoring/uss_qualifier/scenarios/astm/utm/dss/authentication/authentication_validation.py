import random
from datetime import datetime, timedelta

from uas_standards.astm.f3548.v21.constants import (
    Scope,
)

from monitoring.monitorlib.auth import InvalidTokenSignatureAuth
from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.planning_area import (
    PlanningAreaResource,
)
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
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

    Note that this scenario does not verif that a DSS only allows an entity owner to modify the:
    this is covered in other scenarios.
    """

    SUB_TYPE = register_resource_type(
        382, "Subscription, Operational Entity Id, Constraint"
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
        # This is the proper scope for interactions with the DSS in this scenario
        scopes = {Scope.StrategicCoordination: "create and delete subscriptions"}

        # For the 'wrong' scope we pick anything from the available scopes that isn't the SCD or empty scope:
        available_scopes = dss.get_authorized_scopes()
        available_scopes.discard(Scope.StrategicCoordination)
        available_scopes.discard("")

        if len(available_scopes) > 0:
            # Sort the scopes to obtain a deterministic order, pick the first one
            available_scopes = sorted(available_scopes)
            self._wrong_scope = available_scopes[0]
            scopes[
                self._wrong_scope
            ] = "Attempt to query subscriptions with wrong scope"
        else:
            self._wrong_scope = None

        self._test_missing_scope = False
        if dss.can_use_scope(""):
            scopes[""] = "Attempt to query subscriptions with missing scope"
            self._test_missing_scope = True

        # Note: .get_instance should be called once we know every scope we will need,
        #  in order to guarantee that they are indeed available.
        self._dss = dss.get_instance(scopes)

        self._pid = [self._dss.participant_id]
        self._test_id = id_generator.id_factory.make_id(self.SUB_TYPE)
        self._planning_area = planning_area.specification

        # Build a ready-to-use 4D volume with no specified time for searching
        # the currently active subscriptions
        self._planning_area_volume4d = Volume4D(
            volume=self._planning_area.volume,
        )

        self._sub_params = self._planning_area.get_new_subscription_params(
            subscription_id=self._test_id,
            # Set this slightly in the past: we will update the subscriptions
            # to a later value that still needs to be roughly 'now' without getting into the future
            start_time=datetime.now().astimezone() - timedelta(seconds=10),
            duration=timedelta(minutes=20),
            # This is a planning area without constraint processing
            notify_for_op_intents=True,
            notify_for_constraints=False,
        )

        # Session that won't provide a token at all
        self._no_auth_session = UTMClientSession(self._dss.base_url, auth_adapter=None)

        # Session that should provide a well-formed token with a wrong signature
        self._invalid_token_session = UTMClientSession(
            self._dss.base_url, auth_adapter=InvalidTokenSignatureAuth()
        )

        generic_validator = GenericAuthValidator(
            self, self._dss, Scope.StrategicCoordination
        )

        self._sub_validator = SubscriptionAuthValidator(
            scenario=self,
            generic_validator=generic_validator,
            dss=self._dss,
            test_id=self._test_id,
            planning_area=self._planning_area,
            planning_area_volume4d=self._planning_area_volume4d,
            no_auth_session=self._no_auth_session,
            invalid_token_session=self._invalid_token_session,
            test_wrong_scope=self._wrong_scope,
            test_missing_scope=self._test_missing_scope,
        )

        self._oir_validator = OperationalIntentRefAuthValidator(
            scenario=self,
            generic_validator=generic_validator,
            dss=self._dss,
            test_id=self._test_id,
            planning_area=self._planning_area,
            planning_area_volume4d=self._planning_area_volume4d,
            no_auth_session=self._no_auth_session,
            invalid_token_session=self._invalid_token_session,
            test_wrong_scope=self._wrong_scope,
            test_missing_scope=self._test_missing_scope,
        )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self._setup_case()
        self.begin_test_case("Endpoint authorization")

        if self._wrong_scope:
            self.record_note(
                "wrong_scope",
                f"Incorrect scope testing enabled with scope {self._wrong_scope}.",
            )
        else:
            self.record_note("wrong_scope", "Incorrect scope testing disabled.")

        if self._test_missing_scope:
            self.record_note("missing_scope", "Missing scope testing enabled.")
        else:
            self.record_note("missing_scope", "Missing scope testing disabled.")

        self.begin_test_step("Subscription endpoints authentication")
        self._sub_validator.verify_sub_endpoints_authentication()

        self.end_test_step()

        self.begin_test_step("Operational intents endpoints authentication")
        self._oir_validator.verify_oir_endpoints_authentication()
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
        # TODO cleanly move this into the test fragments once the relevant PRs (notably #535) are merged
        with self.check(
            "Operational intent references can be queried by ID", self._pid
        ) as check:
            try:
                oir, q = self._dss.get_op_intent_reference(self._test_id)
                self.record_query(q)
            except QueryError as qe:
                self.record_queries(qe.queries)
                if qe.queries[0].response.status_code == 404:
                    return  # All is good
                else:
                    query = qe.queries[0]
                    check.record_failed(
                        summary=f"Could not query OIR {self._test_id}",
                        details=f"When attempting to query OIR {self._test_id} from the DSS, received {query.response.status_code}: {qe.msg}",
                        query_timestamps=[query.request.timestamp],
                    )

        with self.check(
            "Operational intent references can be deleted by their owner", self._pid
        ):
            try:
                oir, subs, q = self._dss.delete_op_intent(oir.id, oir.ovn)
                self.record_query(q)
            except QueryError as qe:
                self.record_queries(qe.queries)
                query = qe.queries[0]
                check.record_failed(
                    summary=f"Could not remove op intent reference {self._test_id}",
                    details=f"When attempting to remove op intent reference {self._test_id} from the DSS, received {query.status_code}: {qe.msg}",
                    query_timestamps=[query.request.timestamp],
                )
                self._dss.delete_op_intent(oir.id, oir.ovn)

        test_step_fragments.cleanup_sub(self, self._dss, self._test_id)

    def _ensure_no_active_subs_exist(self):
        test_step_fragments.cleanup_active_subs(
            self,
            self._dss,
            self._planning_area_volume4d,
        )

    def cleanup(self):
        self.begin_cleanup()
        self._ensure_test_entities_dont_exist()
        self.end_cleanup()
