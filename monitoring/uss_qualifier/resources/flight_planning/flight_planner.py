from typing import Tuple, Optional, Set
from urllib.parse import urlparse
from implicitdict import ImplicitDict
from monitoring.monitorlib import infrastructure, fetch
from monitoring.monitorlib.clients.flight_planning.client import (
    PlanningActivityError,
    FlightPlannerClient,
)
from monitoring.monitorlib.clients.flight_planning.client_scd import (
    SCDFlightPlannerClient,
)
from monitoring.monitorlib.clients.flight_planning.client_v1 import (
    V1FlightPlannerClient,
)
from monitoring.monitorlib.clients.flight_planning.flight_info import (
    ExecutionStyle,
    FlightInfo,
    BasicFlightPlanInformation,
    ASTMF354821OpIntentInformation,
    FlightAuthorisationData,
    AirspaceUsageState,
    UasState,
)
from monitoring.monitorlib.clients.flight_planning.planning import (
    PlanningActivityResult,
    FlightPlanStatus,
    AdvisoryInclusion,
)
from monitoring.monitorlib.fetch import QueryError, Query
from monitoring.monitorlib.geotemporal import Volume4D, Volume4DCollection
from uas_standards.interuss.automated_testing.scd.v1.api import (
    InjectFlightResponseResult,
    DeleteFlightResponseResult,
    InjectFlightResponse,
    DeleteFlightResponse,
    InjectFlightRequest,
    ClearAreaResponse,
    OperationalIntentState,
    ClearAreaOutcome,
)


class FlightPlannerConfiguration(ImplicitDict):
    participant_id: str
    """ID of the flight planner into which test data can be injected"""

    scd_injection_base_url: Optional[str]
    """Base URL for the flight planner's implementation of the interfaces/automated_testing/scd/v1/scd.yaml API"""

    v1_base_url: Optional[str]
    """Base URL for the flight planner's implementation of the interfaces/automated_testing/flight_planning/v1/flight_planning.yaml API"""

    timeout_seconds: Optional[float] = None
    """Number of seconds to allow for requests to this flight planner.  If None, use default."""

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        if "v1_base_url" not in self and "scd_injection_base_url" not in self:
            raise ValueError(
                "One of `scd_injection_base_url` or `v1_base_url` must be specified"
            )
        if "scd_injection_base_url" in self and self.scd_injection_base_url:
            try:
                urlparse(self.scd_injection_base_url)
            except ValueError:
                raise ValueError(
                    "FlightPlannerConfiguration.scd_injection_base_url must be a URL"
                )
        if "v1_base_url" in self and self.v1_base_url:
            try:
                urlparse(self.v1_base_url)
            except ValueError:
                raise ValueError("FlightPlannerConfiguration.v1_base_url must be a URL")

    def to_client(
        self, auth_adapter: infrastructure.AuthAdapter
    ) -> FlightPlannerClient:
        if "scd_injection_base_url" in self and self.scd_injection_base_url:
            session = infrastructure.UTMClientSession(
                self.scd_injection_base_url, auth_adapter, self.timeout_seconds
            )
            return SCDFlightPlannerClient(session, self.participant_id)
        elif "v1_base_url" in self and self.v1_base_url:
            session = infrastructure.UTMClientSession(
                self.v1_base_url, auth_adapter, self.timeout_seconds
            )
            return V1FlightPlannerClient(session, self.participant_id)
        raise ValueError(
            "Could not construct FlightPlannerClient from provided configuration"
        )


class FlightPlanner:
    """Manages the state and the interactions with flight planner USS.

    Note: this class will be deprecated in favor of FlightPlannerClient."""

    def __init__(
        self,
        config: FlightPlannerConfiguration,
        auth_adapter: infrastructure.AuthAdapter,
    ):
        self.config = config
        self.client = config.to_client(auth_adapter)

        # Flights injected by this target.
        self.created_flight_ids: Set[str] = set()

    def __repr__(self):
        return "FlightPlanner({}, {})".format(
            self.config.participant_id, self.config.scd_injection_base_url
        )

    @property
    def name(self) -> str:
        return self.config.participant_id

    @property
    def participant_id(self):
        return self.config.participant_id

    def request_flight(
        self,
        request: InjectFlightRequest,
        flight_id: Optional[str] = None,
    ) -> Tuple[InjectFlightResponse, fetch.Query, str, Optional[AdvisoryInclusion]]:
        usage_states = {
            OperationalIntentState.Accepted: AirspaceUsageState.Planned,
            OperationalIntentState.Activated: AirspaceUsageState.InUse,
            OperationalIntentState.Nonconforming: AirspaceUsageState.InUse,
            OperationalIntentState.Contingent: AirspaceUsageState.InUse,
        }
        uas_states = {
            OperationalIntentState.Accepted: UasState.Nominal,
            OperationalIntentState.Activated: UasState.Nominal,
            OperationalIntentState.Nonconforming: UasState.OffNominal,
            OperationalIntentState.Contingent: UasState.Contingent,
        }
        if (
            request.operational_intent.state
            in (OperationalIntentState.Accepted, OperationalIntentState.Activated)
            and request.operational_intent.off_nominal_volumes
        ):
            # This invalid request can no longer be represented with a standard flight planning request; reject it at the client level instead
            raise ValueError(
                f"Request for nominal {request.operational_intent.state} operational intent is invalid because it contains off-nominal volumes"
            )
        v4c = Volume4DCollection.from_interuss_scd_api(
            request.operational_intent.volumes
        ) + Volume4DCollection.from_interuss_scd_api(
            request.operational_intent.off_nominal_volumes
        )
        basic_information = BasicFlightPlanInformation(
            usage_state=usage_states[request.operational_intent.state],
            uas_state=uas_states[request.operational_intent.state],
            area=v4c,
        )
        astm_f3548v21 = ASTMF354821OpIntentInformation(
            priority=request.operational_intent.priority
        )
        uspace_flight_authorisation = ImplicitDict.parse(
            request.flight_authorisation, FlightAuthorisationData
        )
        flight_info = FlightInfo(
            basic_information=basic_information,
            astm_f3548_21=astm_f3548v21,
            uspace_flight_authorisation=uspace_flight_authorisation,
        )

        if not flight_id:
            try:
                resp = self.client.try_plan_flight(
                    flight_info, ExecutionStyle.IfAllowed
                )
            except PlanningActivityError as e:
                raise QueryError(str(e), e.queries)
            flight_id = resp.flight_id
        else:
            try:
                resp = self.client.try_update_flight(
                    flight_id, flight_info, ExecutionStyle.IfAllowed
                )
            except PlanningActivityError as e:
                raise QueryError(str(e), e.queries)

        if resp.activity_result == PlanningActivityResult.Failed:
            result = InjectFlightResponseResult.Failed
        elif resp.activity_result == PlanningActivityResult.NotSupported:
            result = InjectFlightResponseResult.NotSupported
        elif resp.activity_result == PlanningActivityResult.Rejected:
            result = InjectFlightResponseResult.Rejected
        elif resp.activity_result == PlanningActivityResult.Completed:
            if resp.flight_plan_status == FlightPlanStatus.Planned:
                result = InjectFlightResponseResult.Planned
            elif resp.flight_plan_status == FlightPlanStatus.OkToFly:
                result = InjectFlightResponseResult.ReadyToFly
            elif resp.flight_plan_status == FlightPlanStatus.OffNominal:
                result = InjectFlightResponseResult.ReadyToFly
            else:
                raise NotImplementedError(
                    f"Unable to handle '{resp.flight_plan_status}' FlightPlanStatus with {resp.activity_result} PlanningActivityResult"
                )
            self.created_flight_ids.add(flight_id)
        else:
            raise NotImplementedError(
                f"Unable to handle '{resp.activity_result}' PlanningActivityResult"
            )

        response = InjectFlightResponse(
            result=result,
            operational_intent_id="<not provided>",
        )

        return response, resp.queries[0], flight_id, resp.includes_advisories

    def cleanup_flight(
        self, flight_id: str
    ) -> Tuple[DeleteFlightResponse, fetch.Query]:
        try:
            resp = self.client.try_end_flight(flight_id, ExecutionStyle.IfAllowed)
        except PlanningActivityError as e:
            raise QueryError(str(e), e.queries)

        if (
            resp.activity_result == PlanningActivityResult.Completed
            and resp.flight_plan_status == FlightPlanStatus.Closed
        ):
            self.created_flight_ids.remove(flight_id)
            return (
                DeleteFlightResponse(result=DeleteFlightResponseResult.Closed),
                resp.queries[0],
            )
        else:
            return (
                DeleteFlightResponse(result=DeleteFlightResponseResult.Failed),
                resp.queries[0],
            )

    def get_readiness(self) -> Tuple[Optional[str], Query]:
        try:
            resp = self.client.report_readiness()
        except PlanningActivityError as e:
            return str(e), e.queries[0]
        return None, resp.queries[0]

    def clear_area(self, extent: Volume4D) -> Tuple[ClearAreaResponse, fetch.Query]:
        try:
            resp = self.client.clear_area(extent)
        except PlanningActivityError as e:
            raise QueryError(str(e), e.queries)
        success = False if resp.errors else True
        return (
            ClearAreaResponse(
                outcome=ClearAreaOutcome(
                    success=success,
                    timestamp=resp.queries[0].response.reported,
                )
            ),
            resp.queries[0],
        )
