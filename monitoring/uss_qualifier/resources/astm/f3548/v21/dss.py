from __future__ import annotations

import datetime
import uuid
from enum import Enum
from typing import Tuple, List, Dict, Optional
from urllib.parse import urlparse

import s2sphere
from implicitdict import ImplicitDict
from uas_standards.astm.f3548.v21.api import (
    QueryOperationalIntentReferenceParameters,
    Volume4D,
    OperationalIntentReference,
    QueryOperationalIntentReferenceResponse,
    OperationalIntent,
    GetOperationalIntentDetailsResponse,
    PutOperationalIntentReferenceParameters,
    EntityOVN,
    OperationalIntentState,
    ImplicitSubscriptionParameters,
    UssBaseURL,
    ChangeOperationalIntentReferenceResponse,
    SubscriberToNotify,
    SetUssAvailabilityStatusParameters,
    UssAvailabilityState,
    UssAvailabilityStatusResponse,
    GetOperationalIntentReferenceResponse,
    OPERATIONS,
    OperationID,
    GetOperationalIntentTelemetryResponse,
    VehicleTelemetry,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib import infrastructure, fetch
from monitoring.monitorlib.fetch import QueryType, Query, query_and_describe
from monitoring.monitorlib.fetch import scd as fetch
from monitoring.monitorlib.fetch.scd import FetchedSubscription, FetchedSubscriptions
from monitoring.monitorlib.inspection import calling_function_name, fullname
from monitoring.monitorlib.mutate import scd as mutate
from monitoring.monitorlib.mutate.scd import MutatedSubscription
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource
from monitoring.uss_qualifier.resources.resource import Resource

# A base URL for a USS that is not expected to be ever called
# Used in scenarios where we mimic the behavior of a USS and need to provide a base URL.
# As the area used for tests is cleared before the tests, there is no need to have this URL be reachable.
DUMMY_USS_BASE_URL = "https://dummy.uss"


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
    _scopes_authorized: Set[str]

    def __init__(
        self,
        participant_id: str,
        base_url: str,
        has_private_address: Optional[bool],
        auth_adapter: infrastructure.AuthAdapter,
        scopes_authorized: List[str],
    ):
        self.participant_id = participant_id
        self.base_url = base_url
        if has_private_address is not None:
            self.has_private_address = has_private_address
        self.client = infrastructure.UTMClientSession(base_url, auth_adapter)
        self._scopes_authorized = set(
            s.value if isinstance(s, Enum) else s for s in scopes_authorized
        )

    def _uses_scope(self, *scopes: Tuple[str]) -> None:
        for scope in scopes:
            if scope not in self._scopes_authorized:
                raise ValueError(
                    f"{fullname(type(self))} client called {calling_function_name(1)} which requires the use of the scope `{scope}`, but this DSSInstance is only authorized to perform actions with the scopes {' or '.join(self._scopes_authorized)}"
                )

    def can_use_scope(self, scope: str) -> bool:
        return scope in self._scopes_authorized

    def with_different_auth(
        self, auth_adapter: AuthAdapterResource, scopes_required: Dict[str, str]
    ) -> DSSInstance:
        auth_adapter.assert_scopes_available(
            scopes_required, "DSSInstance.with_different_auth"
        )
        return DSSInstance(
            participant_id=self.participant_id,
            base_url=self.base_url,
            has_private_address=self.has_private_address,
            auth_adapter=auth_adapter.adapter,
            scopes_authorized=list(scopes_required),
        )

    def find_op_intent(
        self, extent: Volume4D
    ) -> Tuple[List[OperationalIntentReference], Query]:
        self._uses_scope(Scope.StrategicCoordination)
        op = OPERATIONS[OperationID.QueryOperationalIntentReferences]
        req = QueryOperationalIntentReferenceParameters(area_of_interest=extent)
        query = query_and_describe(
            self.client,
            op.verb,
            op.path,
            QueryType.F3548v21DSSQueryOperationalIntentReferences,
            self.participant_id,
            scope=Scope.StrategicCoordination,
            json=req,
        )
        if query.status_code != 200:
            result = None
        else:
            result = ImplicitDict.parse(
                query.response.json, QueryOperationalIntentReferenceResponse
            ).operational_intent_references
        return result, query

    def get_op_intent_reference(
        self,
        op_intent_id: str,
    ) -> Tuple[OperationalIntentReference, Query]:
        """
        Retrieve an OP Intent from the DSS, using only its ID
        """
        self._uses_scope(Scope.StrategicCoordination)
        op = OPERATIONS[OperationID.GetOperationalIntentReference]
        query = query_and_describe(
            self.client,
            op.verb,
            op.path.format(entityid=op_intent_id),
            QueryType.F3548v21DSSGetOperationalIntentReference,
            self.participant_id,
            scope=Scope.StrategicCoordination,
        )
        if query.status_code != 200:
            result = None
        else:
            result = ImplicitDict.parse(
                query.response.json, GetOperationalIntentReferenceResponse
            ).operational_intent_reference
        return result, query

    def get_full_op_intent(
        self,
        op_intent_ref: OperationalIntentReference,
        uss_participant_id: Optional[str] = None,
    ) -> Tuple[OperationalIntent, Query]:
        result, query = self.get_full_op_intent_without_validation(
            op_intent_ref,
            uss_participant_id,
        )
        if query.status_code != 200:
            result = None
        else:
            result = ImplicitDict.parse(
                query.response.json, GetOperationalIntentDetailsResponse
            ).operational_intent
        return result, query

    def get_full_op_intent_without_validation(
        self,
        op_intent_ref: OperationalIntentReference,
        uss_participant_id: Optional[str] = None,
    ) -> Tuple[Dict, Query]:
        """
        GET OperationalIntent without validating, as invalid data expected for negative tests

        Returns:
            returns the response json when query is successful
        """
        self._uses_scope(Scope.StrategicCoordination)
        op = OPERATIONS[OperationID.GetOperationalIntentDetails]
        query = query_and_describe(
            self.client,
            op.verb,
            f"{op_intent_ref.uss_base_url}{op.path.format(entityid=op_intent_ref.id)}",
            QueryType.F3548v21USSGetOperationalIntentDetails,
            uss_participant_id,
            scope=Scope.StrategicCoordination,
        )
        result = None
        if query.status_code == 200:
            result = query.response.json

        return result, query

    def get_op_intent_telemetry(
        self,
        op_intent_ref: OperationalIntentReference,
        uss_participant_id: Optional[str] = None,
    ) -> Tuple[Optional[VehicleTelemetry], Query]:
        self._uses_scope(Scope.ConformanceMonitoringForSituationalAwareness)
        op = OPERATIONS[OperationID.GetOperationalIntentTelemetry]
        query = query_and_describe(
            self.client,
            op.verb,
            f"{op_intent_ref.uss_base_url}{op.path.format(entityid=op_intent_ref.id)}",
            QueryType.F3548v21USSGetOperationalIntentTelemetry,
            uss_participant_id,
            scope=Scope.ConformanceMonitoringForSituationalAwareness,
        )
        if query.status_code == 200:
            result: GetOperationalIntentTelemetryResponse = ImplicitDict.parse(
                query.response.json, GetOperationalIntentTelemetryResponse
            )
            telemetry = result.telemetry if "telemetry" in result else None
            return telemetry, query
        else:
            return None, query

    def put_op_intent(
        self,
        extents: List[Volume4D],
        key: List[EntityOVN],
        state: OperationalIntentState,
        base_url: UssBaseURL,
        id: Optional[str] = None,
        ovn: Optional[str] = None,
    ) -> Tuple[
        Optional[OperationalIntentReference],
        Optional[List[SubscriberToNotify]],
        Query,
    ]:
        self._uses_scope(Scope.StrategicCoordination)
        oi_uuid = str(uuid.uuid4()) if id is None else id
        if ovn is None:
            op = OPERATIONS[OperationID.CreateOperationalIntentReference]
            url = op.path.format(entityid=oi_uuid)
            query_type = QueryType.F3548v21DSSCreateOperationalIntentReference
        else:
            op = OPERATIONS[OperationID.UpdateOperationalIntentReference]
            url = op.path.format(entityid=oi_uuid, ovn=ovn)
            query_type = QueryType.F3548v21DSSUpdateOperationalIntentReference

        req = PutOperationalIntentReferenceParameters(
            extents=extents,
            key=key,
            state=state,
            uss_base_url=base_url,
            new_subscription=ImplicitSubscriptionParameters(uss_base_url=base_url),
        )
        query = query_and_describe(
            self.client,
            op.verb,
            url,
            query_type,
            self.participant_id,
            scope=Scope.StrategicCoordination,
            json=req,
        )
        if query.status_code != 200 and query.status_code != 201:
            return None, None, query
        else:
            result = ChangeOperationalIntentReferenceResponse(
                ImplicitDict.parse(
                    query.response.json, ChangeOperationalIntentReferenceResponse
                )
            )
            return result.operational_intent_reference, result.subscribers, query

    def delete_op_intent(
        self,
        id: str,
        ovn: str,
    ) -> Tuple[
        Optional[OperationalIntentReference],
        Optional[List[SubscriberToNotify]],
        Query,
    ]:
        self._uses_scope(Scope.StrategicCoordination)
        op = OPERATIONS[OperationID.DeleteOperationalIntentReference]
        query = query_and_describe(
            self.client,
            op.verb,
            op.path.format(entityid=id, ovn=ovn),
            QueryType.F3548v21DSSDeleteOperationalIntentReference,
            self.participant_id,
            scope=Scope.StrategicCoordination,
        )
        if query.status_code != 200:
            return None, None, query
        else:
            try:
                result = ChangeOperationalIntentReferenceResponse(
                    ImplicitDict.parse(
                        query.response.json, ChangeOperationalIntentReferenceResponse
                    )
                )
                return result.operational_intent_reference, result.subscribers, query
            except ValueError as e:
                return None, None, query

    def set_uss_availability(
        self,
        uss_id: str,
        available: bool,
        version: str = "",
    ) -> Tuple[Optional[str], Query]:
        """
        Returns:
            A tuple composed of
            1) the new version of the USS availability, or None if the query failed;
            2) the query.
        """
        self._uses_scope(Scope.AvailabilityArbitration)
        if available:
            availability = UssAvailabilityState.Normal
        else:
            availability = UssAvailabilityState.Down

        req = SetUssAvailabilityStatusParameters(
            old_version=version,
            availability=availability,
        )
        op = OPERATIONS[OperationID.SetUssAvailability]
        query = query_and_describe(
            self.client,
            op.verb,
            op.path.format(uss_id=uss_id),
            QueryType.F3548v21DSSSetUssAvailability,
            self.participant_id,
            scope=Scope.AvailabilityArbitration,
            json=req,
        )
        if query.status_code != 200:
            return None, query
        else:
            result = UssAvailabilityStatusResponse(
                ImplicitDict.parse(query.response.json, UssAvailabilityStatusResponse)
            )
            return result.version, query

    def search_subscriptions(
        self,
        volume: Volume4D,
    ) -> FetchedSubscriptions:
        self._uses_scope(Scope.StrategicCoordination)
        return fetch.search_subscriptions(
            self.client,
            volume,
            self.participant_id,
        )

    def upsert_subscription(
        self,
        area_vertices: s2sphere.LatLngRect,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        base_url: str,
        sub_id: str,
        notify_for_op_intents: bool,
        notify_for_constraints: bool,
        min_alt_m: float,
        max_alt_m: float,
        version: Optional[str] = None,
    ) -> MutatedSubscription:
        self._uses_scope(Scope.StrategicCoordination)
        return mutate.upsert_subscription(
            self.client,
            area_vertices,
            start_time,
            end_time,
            base_url,
            sub_id,
            notify_for_op_intents,
            notify_for_constraints,
            min_alt_m,
            max_alt_m,
            version,
            self.participant_id,
        )

    def get_subscription(self, sub_id: str) -> FetchedSubscription:
        """
        Retrieve a subscription from the DSS, using only its ID
        """
        self._uses_scope(Scope.StrategicCoordination)
        return fetch.get_subscription(
            self.client,
            sub_id,
            self.participant_id,
        )

    def delete_subscription(self, sub_id: str, sub_version: str) -> MutatedSubscription:
        self._uses_scope(Scope.StrategicCoordination)
        return mutate.delete_subscription(
            self.client,
            sub_id,
            sub_version,
            self.participant_id,
        )


class DSSInstanceResource(Resource[DSSInstanceSpecification]):
    _specification: DSSInstanceSpecification
    _auth_adapter: AuthAdapterResource

    def __init__(
        self,
        specification: DSSInstanceSpecification,
        auth_adapter: AuthAdapterResource,
    ):
        self._specification = specification
        self._auth_adapter = auth_adapter

    def can_use_scope(self, scope: str) -> bool:
        return scope in self._auth_adapter.scopes

    def get_instance(self, scopes_required: Dict[str, str]) -> DSSInstance:
        """Get a client object ready to be used.

        This method should generally be called in the constructor of a test
        scenario so that the MissingResourceError is raised during scenario
        construction, which may cause the test scenario to be skipped when
        the necessary scopes are not available.

        Args:
            scopes_required: Mapping between F3548-21 scopes that the client
                object will need to use and the reasons each scope will need to
                be used.

        Returns: Client object, ready to be used to perform ecosystem tasks.

        Raises:
            * MissingResourceError if auth adapter for this resource does not
              support the specified scopes that will be used by the client
              object.
        """
        self._auth_adapter.assert_scopes_available(
            scopes_required, fullname(type(self))
        )
        return DSSInstance(
            self._specification.participant_id,
            self._specification.base_url,
            self._specification.get("has_private_address"),
            self._auth_adapter.adapter,
            list(scopes_required),
        )

    def is_same_as(self, other: DSSInstanceResource) -> bool:
        return (
            self._specification == other._specification
            and self._auth_adapter is other._auth_adapter
        )


class DSSInstancesSpecification(ImplicitDict):
    dss_instances: List[DSSInstanceSpecification]


class DSSInstancesResource(Resource[DSSInstancesSpecification]):
    dss_instances: List[DSSInstanceResource]

    def __init__(
        self,
        specification: DSSInstancesSpecification,
        auth_adapter: AuthAdapterResource,
    ):
        self.dss_instances = [
            DSSInstanceResource(
                specification=s,
                auth_adapter=auth_adapter,
            )
            for s in specification.dss_instances
        ]
