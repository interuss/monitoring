from typing import List, Optional, Tuple

from loguru import logger
import s2sphere
from implicitdict import ImplicitDict
from uas_standards.interuss.automated_testing.rid.v1 import (
    observation as observation_api,
)
from uas_standards.interuss.automated_testing.rid.v1.constants import Scope

from monitoring.monitorlib import fetch, infrastructure
from monitoring.monitorlib.fetch import QueryType
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.resources.resource import Resource
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource


class RIDSystemObserver(object):
    participant_id: str
    base_url: str
    session: infrastructure.UTMClientSession

    def __init__(
        self,
        participant_id: str,
        base_url: str,
        auth_adapter: infrastructure.AuthAdapter,
    ):
        self.session = UTMClientSession(base_url, auth_adapter)
        self.participant_id = participant_id
        self.base_url = base_url

    def observe_system(
        self, rect: s2sphere.LatLngRect
    ) -> Tuple[Optional[observation_api.GetDisplayDataResponse], fetch.Query]:
        url = "/display_data?view={},{},{},{}".format(
            rect.lo().lat().degrees,
            rect.lo().lng().degrees,
            rect.hi().lat().degrees,
            rect.hi().lng().degrees,
        )
        query = fetch.query_and_describe(
            self.session,
            "GET",
            url,
            scope=Scope.Observe,
            participant_id=self.participant_id,
            query_type=QueryType.InterUSSRIDObservationV1GetDisplayData,
        )
        try:
            result = (
                ImplicitDict.parse(
                    query.response.json, observation_api.GetDisplayDataResponse
                )
                if query.status_code == 200
                else None
            )
        except ValueError as e:
            logger.error("Error parsing observation response: {}", e)
            result = None
        return result, query

    def observe_flight_details(
        self, flight_id: str
    ) -> Tuple[Optional[observation_api.GetDetailsResponse], fetch.Query]:
        query = fetch.query_and_describe(
            self.session,
            "GET",
            f"/display_data/{flight_id}",
            scope=Scope.Observe,
            participant_id=self.participant_id,
            query_type=QueryType.InterUSSRIDObservationV1GetDetails,
        )
        # Record query metadata for later use in the aggregate checks
        query.participant_id = self.participant_id
        try:
            result = (
                ImplicitDict.parse(
                    query.response.json, observation_api.GetDetailsResponse
                )
                if query.status_code == 200
                else None
            )
        except ValueError as e:
            logger.error("Error parsing observation details response: {}", e)
            result = None
        return result, query


class ObserverConfiguration(ImplicitDict):
    participant_id: str
    """Participant ID of the observer providing a view of RID data in the system"""

    observation_base_url: str
    """Base URL for the observer's implementation of the interfaces/automated-testing/rid/observation.yaml API"""


class NetRIDObserversSpecification(ImplicitDict):
    observers: List[ObserverConfiguration]


class NetRIDObserversResource(Resource[NetRIDObserversSpecification]):
    observers: List[RIDSystemObserver]

    def __init__(
        self,
        specification: NetRIDObserversSpecification,
        resource_origin: str,
        auth_adapter: AuthAdapterResource,
    ):
        super(NetRIDObserversResource, self).__init__(specification, resource_origin)
        auth_adapter.assert_scopes_available(
            scopes_required={
                Scope.Observe: "observe RID flights visible to user from USSs under test"
            },
            consumer_name=self.__class__.__name__,
        )

        self.observers = [
            RIDSystemObserver(
                o.participant_id,
                o.observation_base_url,
                auth_adapter.adapter,
            )
            for o in specification.observers
        ]
