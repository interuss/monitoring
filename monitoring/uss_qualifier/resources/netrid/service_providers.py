import datetime
from typing import List
from urllib.parse import urlparse

from implicitdict import ImplicitDict

from monitoring.monitorlib import fetch, infrastructure
from monitoring.monitorlib.rid_automated_testing.injection_api import (
    CreateTestParameters,
    SCOPE_RID_QUALIFIER_INJECT,
)
from monitoring.uss_qualifier.resources.resource import Resource
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource


class ServiceProviderConfiguration(ImplicitDict):
    participant_id: str
    """ID of the NetRID Service Provider into which test data can be injected"""

    injection_base_url: str
    """Base URL for the Service Provider's implementation of the interfaces/automated-testing/rid/injection.yaml API"""

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        try:
            urlparse(self.injection_base_url)
        except ValueError:
            raise ValueError(
                "ServiceProviderConfiguration.injection_base_url must be a URL"
            )


class NetRIDServiceProvidersSpecification(ImplicitDict):
    service_providers: List[ServiceProviderConfiguration]


class NetRIDServiceProvider(object):
    participant_id: str
    base_url: str
    client: infrastructure.UTMClientSession

    def __init__(
        self,
        participant_id: str,
        base_url: str,
        auth_adapter: infrastructure.AuthAdapter,
    ):
        self.participant_id = participant_id
        self.base_url = base_url
        self.client = infrastructure.UTMClientSession(base_url, auth_adapter)

    def submit_test(self, request: CreateTestParameters, test_id: str) -> fetch.Query:
        return fetch.query_and_describe(
            self.client,
            "PUT",
            url=f"/tests/{test_id}",
            json=request,
            scope=SCOPE_RID_QUALIFIER_INJECT,
        )

    def delete_test(self, test_id: str, version: str) -> fetch.Query:
        return fetch.query_and_describe(
            self.client,
            "DELETE",
            url=f"/tests/{test_id}/{version}",
            scope=SCOPE_RID_QUALIFIER_INJECT,
        )


class NetRIDServiceProviders(Resource[NetRIDServiceProvidersSpecification]):
    service_providers: List[NetRIDServiceProvider]

    def __init__(
        self,
        specification: NetRIDServiceProvidersSpecification,
        auth_adapter: AuthAdapterResource,
    ):
        self.service_providers = [
            NetRIDServiceProvider(
                s.participant_id, s.injection_base_url, auth_adapter.adapter
            )
            for s in specification.service_providers
        ]
