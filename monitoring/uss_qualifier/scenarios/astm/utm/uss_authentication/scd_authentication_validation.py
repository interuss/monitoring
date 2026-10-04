import uuid

from uas_standards.astm.f3548.v21.api import (
    OPERATIONS,
    OperationalIntentReference,
    OperationID,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.clients.flight_planning.flight_info import (
    AirspaceUsageState,
    UasState,
)
from monitoring.monitorlib.fetch import QueryType
from monitoring.monitorlib.infrastructure import (
    utm_client_session_factory,
)
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstanceResource,
)
from monitoring.uss_qualifier.resources.astm.f3548.v21.uss import (
    USSInstance,
)
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource
from monitoring.uss_qualifier.resources.flight_planning import (
    FlightIntentsResource,
    FlightPlannerResource,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_intent_validation import (
    ExpectedFlightIntent,
    validate_flight_intent_templates,
)
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import (
    OpIntentValidator,
)
from monitoring.uss_qualifier.scenarios.astm.utm.uss_authentication.endpoint_auth_validator import (
    EndpointAuthValidator,
)
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import (
    cleanup_flights,
    plan_flight,
)
from monitoring.uss_qualifier.scenarios.scenario import (
    ScenarioCannotContinueError,
    TestScenario,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class SCDAuthenticationValidation(TestScenario):
    """
    A scenario that verifies that a USS properly authenticates requests to the
    strategic coordination endpoints required by USS0105,1, 3, and 4 with the
    appropriate status code and error response body.
    """

    def __init__(
        self,
        tested_uss: FlightPlannerResource,
        utm_auth: AuthAdapterResource,
        dss: DSSInstanceResource,
        flight_intents: FlightIntentsResource,
    ):
        super().__init__()
        self.tested_uss = tested_uss
        self.utm_auth = utm_auth
        self.flight_1 = self._init_flight_template(flight_intents=flight_intents)
        self.dss = dss.get_instance(
            {
                Scope.StrategicCoordination: "search for operational intent references to obtain USS base URL"
            }
        )
        self.utm_auth.assert_scopes_available(
            scopes_required={
                Scope.StrategicCoordination: "act as a peer USS calling the USS under test"
            },
            consumer_name=f"{self.__class__.__name__} test scenario",
        )

    def _init_flight_template(self, flight_intents: FlightIntentsResource):
        templates = flight_intents.get_flight_intents()
        expected_flight_intents = [
            ExpectedFlightIntent(
                "flight_1",
                "Flight 1",
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
            ),
        ]
        try:
            validate_flight_intent_templates(templates, expected_flight_intents)
        except ValueError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: {e}"
            )
        return templates["flight_1"]

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self.record_note("Tested USS", self.tested_uss.participant_id)

        self.begin_test_case("Setup")
        self.begin_test_step("Successfully plan flight")
        oi_ref = self._resolve_oi_ref()
        uss = self._resolve_uss(oi_ref)
        self.record_note("USS base URL", uss.base_url)
        self.end_test_step()
        self.end_test_case()

        self.begin_test_case("Endpoint authorization")
        self.begin_test_step("Operational Intent endpoints authentication")
        self._verify_endpoint_authentication(uss)
        self.end_test_step()
        self.end_test_case()

        self.end_test_scenario()

    def _resolve_oi_ref(self) -> OperationalIntentReference | None:
        flight = self.flight_1.resolve(self.time_context.evaluate_now())
        with OpIntentValidator(
            self,
            self.tested_uss.client,
            self.dss,
            flight.basic_information.area.bounding_volume.to_f3548v21(),
        ) as validator:
            _, _, as_planned = plan_flight(
                self,
                self.tested_uss.client,
                flight,
            )
            return validator.expect_shared(as_planned)

    def _resolve_uss(self, oi_ref: OperationalIntentReference | None) -> USSInstance:
        if oi_ref is None:
            raise ScenarioCannotContinueError(
                "Could not find the operational intent reference created by the USS under test"
            )

        base_url = oi_ref.uss_base_url
        return USSInstance(
            participant_id=self.tested_uss.participant_id,
            base_url=base_url,
            client=utm_client_session_factory.get_session(
                base_url, self.utm_auth.adapter
            ),
        )

    def _verify_endpoint_authentication(self, uss: USSInstance):
        op = OPERATIONS[OperationID.GetOperationalIntentDetails]
        EndpointAuthValidator(
            scenario=self,
            operation_name="Get operational intent details",
            auth_target=uss,
            client_scopes=self.utm_auth.scopes,
            valid_scopes=[Scope.StrategicCoordination],
            query_kwargs=dict(
                verb=op.verb,
                url=op.path.format(entityid=str(uuid.uuid4())),
                query_type=QueryType.F3548v21USSGetOperationalIntentDetails,
                participant_id=uss.participant_id,
            ),
        ).verify_endpoints_authentication()

    def cleanup(self):
        self.begin_cleanup()
        cleanup_flights(self, [self.tested_uss.client])
        self.end_cleanup()
