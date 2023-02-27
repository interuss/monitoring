import uuid
from typing import Tuple, List, Optional, Set
from urllib.parse import urlparse

from implicitdict import ImplicitDict

from monitoring.monitorlib import infrastructure, fetch
from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.scd import Volume4D
from monitoring.monitorlib.scd_automated_testing.scd_injection_api import (
    InjectFlightResult,
    DeleteFlightResult,
    InjectFlightResponse,
    DeleteFlightResponse,
    InjectFlightRequest,
    Capability,
    ClearAreaResponse,
    ClearAreaRequest,
    SCOPE_SCD_QUALIFIER_INJECT,
)
from uas_standards.interuss.automated_testing.flight_planning.v1.api import (
    StatusResponse,
    CapabilitiesResponse,
)


class FlightPlannerConfiguration(ImplicitDict):
    participant_id: str
    """ID of the flight planner into which test data can be injected"""

    injection_base_url: str
    """Base URL for the flight planner's implementation of the interfaces/automated-testing/scd/scd.yaml API"""

    timeout_seconds: Optional[float] = None
    """Number of seconds to allow for requests to this flight planner.  If None, use default."""

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        try:
            urlparse(self.injection_base_url)
        except ValueError:
            raise ValueError(
                "FlightPlannerConfiguration.injection_base_url must be a URL"
            )


class FlightPlannerInformation(ImplicitDict):
    version: str
    capabilities: List[Capability]
    version_query: fetch.Query
    capabilities_query: fetch.Query


class FlightPlanner:
    """Manages the state and the interactions with flight planner USS"""

    def __init__(
        self,
        config: FlightPlannerConfiguration,
        auth_adapter: infrastructure.AuthAdapter,
    ):
        self.config = config
        self.client = infrastructure.UTMClientSession(
            self.config.injection_base_url, auth_adapter, config.timeout_seconds
        )

        # Flights injected by this target.
        self.created_flight_ids: Set[str] = set()

    def __repr__(self):
        return "FlightPlanner({}, {})".format(
            self.config.participant_id, self.config.injection_base_url
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
    ) -> Tuple[InjectFlightResponse, fetch.Query, str]:
        if not flight_id:
            flight_id = str(uuid.uuid4())
        url = "{}/v1/flights/{}".format(self.config.injection_base_url, flight_id)

        query = fetch.query_and_describe(
            self.client, "PUT", url, json=request, scope=SCOPE_SCD_QUALIFIER_INJECT
        )
        if query.status_code != 200:
            raise QueryError(
                f"Inject flight query to {url} returned {query.status_code}", [query]
            )
        try:
            result = ImplicitDict.parse(
                query.response.get("json", {}), InjectFlightResponse
            )
        except ValueError as e:
            raise QueryError(
                f"Inject flight response from {url} could not be decoded: {str(e)}",
                [query],
            )

        if result.result == InjectFlightResult.Planned:
            self.created_flight_ids.add(flight_id)

        return result, query, flight_id

    def cleanup_flight(
        self, flight_id: str
    ) -> Tuple[DeleteFlightResponse, fetch.Query]:
        url = "{}/v1/flights/{}".format(self.config.injection_base_url, flight_id)
        query = fetch.query_and_describe(
            self.client, "DELETE", url, scope=SCOPE_SCD_QUALIFIER_INJECT
        )
        if query.status_code != 200:
            raise QueryError(
                f"Delete flight query to {url} returned {query.status_code}", [query]
            )
        try:
            result = ImplicitDict.parse(
                query.response.get("json", {}), DeleteFlightResponse
            )
        except ValueError as e:
            raise QueryError(
                f"Delete flight response from {url} could not be decoded: {str(e)}",
                [query],
            )

        if result.result == DeleteFlightResult.Closed:
            self.created_flight_ids.remove(flight_id)
        return result, query

    def get_target_information(self) -> FlightPlannerInformation:
        url_status = "{}/v1/status".format(self.config.injection_base_url)
        version_query = fetch.query_and_describe(
            self.client, "GET", url_status, scope=SCOPE_SCD_QUALIFIER_INJECT
        )
        if version_query.status_code != 200:
            raise QueryError(
                f"Status query to {url_status} returned {version_query.status_code}",
                [version_query],
            )
        try:
            status_body = ImplicitDict.parse(
                version_query.response.get("json", {}), StatusResponse
            )
        except ValueError as e:
            raise QueryError(
                f"Status response from {url_status} could not be decoded: {str(e)}",
                [version_query],
            )
        version = status_body.version if status_body.version is not None else "Unknown"

        url_capabilities = "{}/v1/capabilities".format(self.config.injection_base_url)
        capabilities_query = fetch.query_and_describe(
            self.client, "GET", url_capabilities, scope=SCOPE_SCD_QUALIFIER_INJECT
        )
        if capabilities_query.status_code != 200:
            raise QueryError(
                f"Capabilities query to {url_capabilities} returned {capabilities_query.status_code}",
                [version_query, capabilities_query],
            )
        try:
            capabilities_body = ImplicitDict.parse(
                capabilities_query.response.get("json", {}), CapabilitiesResponse
            )
        except ValueError as e:
            raise QueryError(
                f"Capabilities response from {url_capabilities} could not be decoded: {str(e)}",
                [version_query],
            )

        return FlightPlannerInformation(
            version=version,
            capabilities=capabilities_body.capabilities,
            version_query=version_query,
            capabilities_query=capabilities_query,
        )

    def clear_area(self, extent: Volume4D) -> Tuple[ClearAreaResponse, fetch.Query]:
        req = ClearAreaRequest(request_id=str(uuid.uuid4()), extent=extent)
        url = f"{self.config.injection_base_url}/v1/clear_area_requests"
        query = fetch.query_and_describe(
            self.client, "POST", url, scope=SCOPE_SCD_QUALIFIER_INJECT, json=req
        )
        if query.status_code != 200:
            raise QueryError(
                f"Clear area query to {url} returned {query.status_code}", [query]
            )
        try:
            result = ImplicitDict.parse(
                query.response.get("json", {}), ClearAreaResponse
            )
        except ValueError as e:
            raise QueryError(
                f"Clear area response from {url} could not be decoded: {str(e)}",
                [query],
            )
        return result, query
