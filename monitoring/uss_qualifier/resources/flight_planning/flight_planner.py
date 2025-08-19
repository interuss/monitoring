from urllib.parse import urlparse

from implicitdict import ImplicitDict

from monitoring.monitorlib import infrastructure
from monitoring.monitorlib.clients.flight_planning.client import FlightPlannerClient
from monitoring.monitorlib.clients.flight_planning.client_scd import (
    SCDFlightPlannerClient,
)
from monitoring.monitorlib.clients.flight_planning.client_v1 import (
    V1FlightPlannerClient,
)


class FlightPlannerConfiguration(ImplicitDict):
    participant_id: str
    """ID of the flight planner into which test data can be injected"""

    scd_injection_base_url: str | None
    """Base URL for the flight planner's implementation of the interfaces/automated_testing/scd/v1/scd.yaml API"""

    v1_base_url: str | None
    """Base URL for the flight planner's implementation of the interfaces/automated_testing/flight_planning/v1/flight_planning.yaml API"""

    timeout_seconds: float | None = None
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
