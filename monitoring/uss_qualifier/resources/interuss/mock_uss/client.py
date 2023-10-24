from typing import Tuple, Optional, List

from implicitdict import ImplicitDict

from monitoring.monitorlib import fetch
from monitoring.monitorlib.clients.mock_uss.locality import (
    GetLocalityResponse,
    PutLocalityRequest,
)
from monitoring.monitorlib.infrastructure import AuthAdapter, UTMClientSession
from monitoring.monitorlib.locality import LocalityCode
from monitoring.monitorlib.scd_automated_testing.scd_injection_api import (
    SCOPE_SCD_QUALIFIER_INJECT,
)
from monitoring.uss_qualifier.reports.report import ParticipantID
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource
from monitoring.uss_qualifier.resources.resource import Resource


MOCK_USS_CONFIG_SCOPE = "interuss.mock_uss.configure"


class MockUSSClient(object):
    """Means to communicate with an InterUSS mock_uss instance"""

    def __init__(
        self,
        participant_id: str,
        base_url: str,
        auth_adapter: AuthAdapter,
    ):
        self.session = UTMClientSession(base_url, auth_adapter)
        self.participant_id = participant_id

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
