from __future__ import annotations
from typing import Tuple, List, Dict, Optional
from urllib.parse import urlparse
from loguru import logger
from implicitdict import ImplicitDict

from monitoring.monitorlib import infrastructure, fetch
from monitoring.monitorlib.fetch import QueryType
from monitoring.monitorlib.scd import SCOPE_SC
from monitoring.uss_qualifier.resources.resource import Resource
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource
from uas_standards.astm.f3548.v21.api import (
    QueryOperationalIntentReferenceParameters,
    Volume4D,
    OperationalIntentReference,
    QueryOperationalIntentReferenceResponse,
    OperationalIntent,
    GetOperationalIntentDetailsResponse,
)


class DSSInstanceSpecification(ImplicitDict):
    participant_id: str
    """ID of the USS responsible for this DSS instance"""

    base_url: str
    """Base URL for the DSS instance according to the ASTM F3548-21 API"""

    has_private_address: Optional[bool]
    """Whether this DSS instance is expected to have a private address that is not publicly addressable."""

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        try:
            urlparse(self.base_url)
        except ValueError:
            raise ValueError("DSSInstanceConfiguration.base_url must be a URL")


class DSSInstance(object):
    participant_id: str
    base_url: str
    has_private_address: bool = False
    client: infrastructure.UTMClientSession

    def __init__(
        self,
        participant_id: str,
        base_url: str,
        has_private_address: Optional[bool],
        auth_adapter: infrastructure.AuthAdapter,
    ):
        self.participant_id = participant_id
        self.base_url = base_url
        if has_private_address is not None:
            self.has_private_address = has_private_address
        self.client = infrastructure.UTMClientSession(base_url, auth_adapter)

    def find_op_intent(
        self, extent: Volume4D
    ) -> Tuple[List[OperationalIntentReference], fetch.Query]:
        url = "/dss/v1/operational_intent_references/query"
        req = QueryOperationalIntentReferenceParameters(area_of_interest=extent)
        query = fetch.query_and_describe(
            self.client,
            "POST",
            url,
            QueryType.F3548v21DSSQueryOperationalIntentReferences,
            self.participant_id,
            scope=SCOPE_SC,
            json=req,
        )
        if query.status_code != 200:
            result = None
        else:
            result = ImplicitDict.parse(
                query.response.json, QueryOperationalIntentReferenceResponse
            ).operational_intent_references
        return result, query

    def get_full_op_intent(
        self,
        op_intent_ref: OperationalIntentReference,
        uss_participant_id: Optional[str] = None,
    ) -> Tuple[OperationalIntent, fetch.Query]:
        url = f"{op_intent_ref.uss_base_url}/uss/v1/operational_intents/{op_intent_ref.id}"
        query = fetch.query_and_describe(
            self.client,
            "GET",
            url,
            QueryType.F3548v21USSGetOperationalIntentDetails,
            uss_participant_id,
            scope=SCOPE_SC,
        )
        if query.status_code != 200:
            result = None
        else:
            result = ImplicitDict.parse(
                query.response.json, GetOperationalIntentDetailsResponse
            ).operational_intent
        return result, query

    def get_full_op_intent_without_validation(
        self, op_intent_ref: OperationalIntentReference
    ) -> Tuple[Dict, fetch.Query]:
        """
        GET OperationalIntent without validating, as invalid data expected for negative tests
        Args:
            op_intent_ref:

        Returns:
            returns the response json when query is successful
        """
        url = f"{op_intent_ref.uss_base_url}/uss/v1/operational_intents/{op_intent_ref.id}"
        query = fetch.query_and_describe(
            self.client, "GET", url, scope=SCOPE_SC, participant_id=self.participant_id
        )
        result = None
        if query.status_code == 200:
            result = query.response.json

        return result, query

    def is_same_as(self, other: DSSInstance) -> bool:
        return (
            self.participant_id == other.participant_id
            and self.base_url == other.base_url
            and self.has_private_address == other.has_private_address
        )


class DSSInstanceResource(Resource[DSSInstanceSpecification]):
    dss: DSSInstance

    def __init__(
        self,
        specification: DSSInstanceSpecification,
        auth_adapter: AuthAdapterResource,
    ):
        self.dss = DSSInstance(
            specification.participant_id,
            specification.base_url,
            specification.get("has_private_address"),
            auth_adapter.adapter,
        )

    @classmethod
    def from_dss_instance(cls, dss_instance: DSSInstance) -> DSSInstanceResource:
        self = cls.__new__(cls)
        self.dss = dss_instance
        return self


class DSSInstancesSpecification(ImplicitDict):
    dss_instances: List[DSSInstanceSpecification]


class DSSInstancesResource(Resource[DSSInstancesSpecification]):
    dss_instances: List[DSSInstance]

    def __init__(
        self,
        specification: DSSInstancesSpecification,
        auth_adapter: AuthAdapterResource,
    ):
        self.dss_instances = [
            DSSInstance(
                s.participant_id,
                s.base_url,
                s.has_private_address,
                auth_adapter.adapter,
            )
            for s in specification.dss_instances
        ]
