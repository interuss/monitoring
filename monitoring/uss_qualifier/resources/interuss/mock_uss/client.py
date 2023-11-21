from typing import Optional

from loguru import logger
from implicitdict import ImplicitDict

from monitoring.monitorlib import fetch
from monitoring.monitorlib.clients.flight_planning.client import FlightPlannerClient
from monitoring.monitorlib.clients.flight_planning.client_v1 import (
    V1FlightPlannerClient,
)
from monitoring.monitorlib.clients.mock_uss.locality import (
    GetLocalityResponse,
    PutLocalityRequest,
)
from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.infrastructure import AuthAdapter, UTMClientSession
from monitoring.monitorlib.locality import LocalityCode
from monitoring.monitorlib.scd_automated_testing.scd_injection_api import (
    SCOPE_SCD_QUALIFIER_INJECT,
)
from monitoring.uss_qualifier.reports.report import ParticipantID
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource
from monitoring.uss_qualifier.resources.resource import Resource
from monitoring.monitorlib.clients.mock_uss.interactions import (
    Interaction,
    ListLogsResponse,
)
from typing import Tuple, List
from implicitdict import StringBasedDateTime

MOCK_USS_CONFIG_SCOPE = "interuss.mock_uss.configure"


class MockUSSClient(object):
    """Means to communicate with an InterUSS mock_uss instance"""

    flight_planner: FlightPlannerClient

    def __init__(
        self,
        participant_id: str,
        base_url: str,
        auth_adapter: AuthAdapter,
        timeout_seconds: Optional[float] = None,
    ):
        self.base_url = base_url
        self.session = UTMClientSession(base_url, auth_adapter, timeout_seconds)
        self.participant_id = participant_id
        v1_base_url = base_url + "/flight_planning/v1"
        self.flight_planner = V1FlightPlannerClient(
            UTMClientSession(v1_base_url, auth_adapter, timeout_seconds), participant_id
        )

    def get_status(self) -> fetch.Query:
        return fetch.query_and_describe(
            self.session,
            "GET",
            "/scdsc/v1/status",
            scope=SCOPE_SCD_QUALIFIER_INJECT,
            participant_id=self.participant_id,
        )

    def get_locality(self) -> Tuple[Optional[LocalityCode], fetch.Query]:
        query = fetch.query_and_describe(
            self.session,
            "GET",
            "/configuration/locality",
            participant_id=self.participant_id,
        )
        if query.status_code != 200:
            return None, query
        try:
            resp = ImplicitDict.parse(query.response.json, GetLocalityResponse)
        except ValueError:
            return None, query
        return resp.locality_code, query

    def set_locality(self, locality_code: LocalityCode) -> fetch.Query:
        return fetch.query_and_describe(
            self.session,
            "PUT",
            "/configuration/locality",
            scope=MOCK_USS_CONFIG_SCOPE,
            participant_id=self.participant_id,
            json=PutLocalityRequest(locality_code=locality_code),
        )

    # TODO: Add other methods to interact with the mock USS in other ways (like starting/stopping message signing data collection)

    def get_interactions(
        self, from_time: StringBasedDateTime
    ) -> Tuple[List[Interaction], fetch.Query]:
        """
        Requesting interuss interactions from mock_uss from a given time till now
        Args:
            from_time: the time from which the interactions are requested
        Returns:
            List of Interactions
        """
        url = "{}/mock_uss/interuss_logging/logs?from_time={}".format(
            self.base_url, from_time
        )
        logger.debug(f"Getting interactions from {from_time} : {url}")
        query = fetch.query_and_describe(
            self.session, "GET", url, scope=SCOPE_SCD_QUALIFIER_INJECT
        )
        if query.status_code != 200:
            raise QueryError(
                f"Request to mock uss {url} returned a {query.status_code} ", [query]
            )
        try:
            response = ImplicitDict.parse(query.response.get("json"), ListLogsResponse)
        except KeyError:
            raise QueryError(
                msg=f"RecordedInteractionsResponse from mock_uss response did not contain JSON body",
                queries=[query],
            )
        except ValueError as e:
            raise QueryError(
                msg=f"RecordedInteractionsResponse from mock_uss response contained invalid JSON: {str(e)}",
                queries=[query],
            )

        return response.interactions, query


class MockUSSSpecification(ImplicitDict):
    mock_uss_base_url: str
    """The base URL for the mock USS.

    If the mock USS had scdsc enabled, for instance, then these URLs would be
    valid:
      * <mock_uss_base_url>/mock/scd/uss/v1/reports
      * <mock_uss_base_url>/scdsc/v1/status
    """

    participant_id: ParticipantID
    """Test participant responsible for this mock USS."""

    timeout_seconds: Optional[float] = None
    """Number of seconds to allow for requests to this mock_uss instance.  If None, use default."""


class MockUSSResource(Resource[MockUSSSpecification]):
    mock_uss: MockUSSClient

    def __init__(
        self,
        specification: MockUSSSpecification,
        auth_adapter: AuthAdapterResource,
    ):
        self.mock_uss = MockUSSClient(
            specification.participant_id,
            specification.mock_uss_base_url,
            auth_adapter.adapter,
            specification.timeout_seconds,
        )


class MockUSSsSpecification(ImplicitDict):
    instances: List[MockUSSSpecification]


class MockUSSsResource(Resource[MockUSSsSpecification]):
    mock_uss_instances: List[MockUSSClient]

    def __init__(
        self, specification: MockUSSsSpecification, auth_adapter: AuthAdapterResource
    ):
        self.mock_uss_instances = [
            MockUSSClient(s.participant_id, s.mock_uss_base_url, auth_adapter.adapter)
            for s in specification.instances
        ]
