import uuid
from typing import Tuple, Optional, Set
from urllib.parse import urlparse

from implicitdict import ImplicitDict

from monitoring.monitorlib import infrastructure, fetch
from monitoring.monitorlib.fetch import QueryError, Query
from monitoring.monitorlib.geotemporal import Volume4D
from uas_standards.interuss.automated_testing.scd.v1.api import (
    InjectFlightResponseResult,
    DeleteFlightResponseResult,
    InjectFlightResponse,
    DeleteFlightResponse,
    InjectFlightRequest,
    ClearAreaResponse,
    ClearAreaRequest,
)
from monitoring.monitorlib.scd_automated_testing.scd_injection_api import (
    SCOPE_SCD_QUALIFIER_INJECT,
)
from uas_standards.interuss.automated_testing.scd.v1.api import (
    StatusResponse,
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
            self.client,
            "PUT",
            url,
            json=request,
            scope=SCOPE_SCD_QUALIFIER_INJECT,
            server_id=self.config.participant_id,
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

        if result.result == InjectFlightResponseResult.Planned:
            self.created_flight_ids.add(flight_id)

        return result, query, flight_id

    def cleanup_flight(
        self, flight_id: str
    ) -> Tuple[DeleteFlightResponse, fetch.Query]:
        url = "{}/v1/flights/{}".format(self.config.injection_base_url, flight_id)
        query = fetch.query_and_describe(
            self.client,
            "DELETE",
            url,
            scope=SCOPE_SCD_QUALIFIER_INJECT,
            server_id=self.config.participant_id,
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

        if result.result == DeleteFlightResponseResult.Closed:
            self.created_flight_ids.remove(flight_id)
        return result, query

    def get_readiness(self) -> Tuple[Optional[str], Query]:
        url_status = "{}/v1/status".format(self.config.injection_base_url)
        version_query = fetch.query_and_describe(
            self.client,
            "GET",
            url_status,
            scope=SCOPE_SCD_QUALIFIER_INJECT,
            server_id=self.config.participant_id,
        )
        if version_query.status_code != 200:
            return (
                f"Status query to {url_status} returned {version_query.status_code}",
                version_query,
            )
        try:
            ImplicitDict.parse(version_query.response.get("json", {}), StatusResponse)
        except ValueError as e:
            return (
                f"Status response from {url_status} could not be decoded: {str(e)}",
                version_query,
            )

        return None, version_query

    def clear_area(self, extent: Volume4D) -> Tuple[ClearAreaResponse, fetch.Query]:
        req = ClearAreaRequest(
            request_id=str(uuid.uuid4()), extent=extent.to_f3548v21()
        )
        url = f"{self.config.injection_base_url}/v1/clear_area_requests"
        query = fetch.query_and_describe(
            self.client,
            "POST",
            url,
            scope=SCOPE_SCD_QUALIFIER_INJECT,
            json=req,
            server_id=self.config.participant_id,
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
