from typing import List, Optional, Tuple

from loguru import logger
import s2sphere
from implicitdict import ImplicitDict

from monitoring.monitorlib import fetch, infrastructure
from monitoring.monitorlib.fetch import QueryType
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.monitorlib.rid import RIDVersion
from uas_standards.interuss.automated_testing.rid.v1 import (
    observation as observation_api,
)
from monitoring.uss_qualifier.resources.resource import Resource
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource


class RIDSystemObserver(object):
    participant_id: str
    base_url: str
    session: infrastructure.UTMClientSession
    local_debug: bool

    def __init__(
        self,
        participant_id: str,
        base_url: str,
        auth_adapter: infrastructure.AuthAdapter,
        local_debug: bool,
    ):
        self.session = UTMClientSession(base_url, auth_adapter)
        self.participant_id = participant_id
        self.base_url = base_url
        self.local_debug = local_debug

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
            # TODO replace with 'uas_standards.interuss.automated_testing.rid.v1.constants.Scope.Observe' once
            #  the standard is updated with https://github.com/interuss/uas_standards/pull/11/files
            scope="dss.read.identification_service_areas",
            participant_id=self.participant_id,
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
        self, flight_id: str, rid_version: RIDVersion
    ) -> Tuple[Optional[observation_api.GetDetailsResponse], fetch.Query]:
        query = fetch.query_and_describe(
            self.session,
            "GET",
            f"/display_data/{flight_id}",
            # TODO replace with 'uas_standards.interuss.automated_testing.rid.v1.constants.Scope.Observe' once
            #  the standard is updated with https://github.com/interuss/uas_standards/pull/11/files
            scope="dss.read.identification_service_areas",
            participant_id=self.participant_id,
        )
        # Record query metadata for later use in the aggregate checks
        query.participant_id = self.participant_id
        query.query_type = QueryType.flight_details(rid_version)
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

    local_debug: Optional[bool]
    """Whether this Observer instance is running locally for debugging or development purposes. Mostly used for relaxing
    constraints around encryption.
    Assumed to be true if left unspecified and has_private_address is true, otherwise defaults to false
    """


class NetRIDObserversSpecification(ImplicitDict):
    observers: List[ObserverConfiguration]


class NetRIDObserversResource(Resource[NetRIDObserversSpecification]):
    observers: List[RIDSystemObserver]

    def __init__(
        self,
        specification: NetRIDObserversSpecification,
        auth_adapter: AuthAdapterResource,
    ):
        self.observers = [
            RIDSystemObserver(
                o.participant_id,
                o.observation_base_url,
                auth_adapter.adapter,
                o.local_debug,
            )
            for o in specification.observers
        ]
