import datetime
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from implicitdict import ImplicitDict
from uas_standards.interuss.automated_testing.rid.v1.injection import (
    QueryUserNotificationsResponse,
)

from monitoring.monitorlib import fetch, infrastructure
from monitoring.monitorlib.rid import RIDVersion
from monitoring.monitorlib.rid_automated_testing.injection_api import (
    SCOPE_RID_QUALIFIER_INJECT,
    CreateTestParameters,
)
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource
from monitoring.uss_qualifier.resources.resource import Resource


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
    injection_base_url: str
    injection_client: infrastructure.UTMClientSession

    def __init__(
        self,
        participant_id: str,
        injection_base_url: str,
        auth_adapter: infrastructure.AuthAdapter,
    ):
        self.participant_id = participant_id
        self.injection_base_url = injection_base_url
        self.injection_client = infrastructure.UTMClientSession(
            injection_base_url, auth_adapter
        )

    def submit_test(self, request: CreateTestParameters, test_id: str) -> fetch.Query:
        return fetch.query_and_describe(
            self.injection_client,
            "PUT",
            url=f"/tests/{test_id}",
            json=request,
            scope=SCOPE_RID_QUALIFIER_INJECT,
            participant_id=self.participant_id,
            query_type=fetch.QueryType.InterussRIDAutomatedTestingV1CreateTest,
        )

    def delete_test(self, test_id: str, version: str) -> fetch.Query:
        return fetch.query_and_describe(
            self.injection_client,
            "DELETE",
            url=f"/tests/{test_id}/{version}",
            scope=SCOPE_RID_QUALIFIER_INJECT,
            participant_id=self.participant_id,
            query_type=fetch.QueryType.InterussRIDAutomatedTestingV1DeleteTest,
        )

    def get_user_notifications(
        self,
        after: datetime.datetime,
        before: datetime.datetime,
    ) -> Tuple[QueryUserNotificationsResponse, fetch.Query]:
        q = fetch.query_and_describe(
            self.injection_client,
            "GET",
            url=f"/user_notifications",
            scope=SCOPE_RID_QUALIFIER_INJECT,
            participant_id=self.participant_id,
            query_type=fetch.QueryType.InterussRIDAutomatedTestingV1UserNotifications,
            params={
                "after": after,
                "before": before,
            },
        )

        if q.error_message:
            return QueryUserNotificationsResponse(user_notifications=[]), q

        return ImplicitDict.parse(q.response.json, QueryUserNotificationsResponse), q


class NetRIDServiceProviders(Resource[NetRIDServiceProvidersSpecification]):
    service_providers: List[NetRIDServiceProvider]

    def __init__(
        self,
        specification: NetRIDServiceProvidersSpecification,
        resource_origin: str,
        auth_adapter: AuthAdapterResource,
    ):
        super(NetRIDServiceProviders, self).__init__(specification, resource_origin)
        auth_adapter.assert_scopes_available(
            scopes_required={
                SCOPE_RID_QUALIFIER_INJECT: "inject RID test flight data into USSs under test"
            },
            consumer_name=f"{self.__class__.__name__} resource",
        )

        self.service_providers = [
            NetRIDServiceProvider(
                participant_id=s.participant_id,
                injection_base_url=s.injection_base_url,
                auth_adapter=auth_adapter.adapter,
            )
            for s in specification.service_providers
        ]
