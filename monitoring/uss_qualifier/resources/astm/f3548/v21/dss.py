from __future__ import annotations

import datetime
import uuid
from enum import Enum
from typing import Tuple, List, Dict, Optional, Set
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
    ExchangeRecord,
    ErrorReport,
    AirspaceConflictResponse,
    PutConstraintReferenceParameters,
    ChangeConstraintReferenceResponse,
    ConstraintReference,
    QueryConstraintReferenceParameters,
    QueryConstraintReferencesResponse,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib import infrastructure, fetch
from monitoring.monitorlib.fetch import QueryType, Query, query_and_describe, QueryError
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

    user_participant_ids: Optional[List[str]]
    """IDs of any participants using this DSS instance, apart from the USS responsible for this DSS instance."""

    base_url: str
    """Base URL for the DSS instance according to the ASTM F3548-21 API"""

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        try:
            urlparse(self.base_url)
        except ValueError:
            raise ValueError("DSSInstanceConfiguration.base_url must be a URL")


class DSSInstance(object):
    participant_id: str
    user_participant_ids: List[str]
    base_url: str
    client: infrastructure.UTMClientSession
    _scopes_authorized: Set[str]

    def __init__(
        self,
        participant_id: str,
        user_participant_ids: List[str],
        base_url: str,
        auth_adapter: infrastructure.AuthAdapter,
        scopes_authorized: List[str],
    ):
        self.participant_id = participant_id
        self.user_participant_ids = user_participant_ids
        self.base_url = base_url
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

    def _uses_any_scope(self, *scopes: str) -> str:
        """Validates that at least a required scope is authorized for a request.
        Additionally, returns a valid scope that may be used for the request."""
        for scope in scopes:
            if scope in self._scopes_authorized:
                return scope
        raise ValueError(
            f"{fullname(type(self))} client called {calling_function_name(1)} which requires the use of any of the scopes `{', '.join(scopes)}`, but this DSSInstance is only authorized to perform actions with the scopes {' or '.join(self._scopes_authorized)}"
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
            user_participant_ids=self.user_participant_ids,
            base_url=self.base_url,
            auth_adapter=auth_adapter.adapter,
            scopes_authorized=list(scopes_required),
        )

    def find_op_intent(
        self, extent: Volume4D
    ) -> Tuple[List[OperationalIntentReference], Query]:
        """
        Find operational intents overlapping with a given volume 4D.
        Raises:
            * QueryError: if request failed, if HTTP status code is different than 200, or if the parsing of the response failed.
        """
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
            raise QueryError(
                f"Received code {query.status_code} when attempting to find operational intents in {extent}{f'; error message: `{query.error_message}`' if query.error_message is not None else ''}",
                query,
            )
        else:
            result = query.parse_json_result(QueryOperationalIntentReferenceResponse)
            return result.operational_intent_references, query

    def get_op_intent_reference(
        self,
        op_intent_id: str,
    ) -> Tuple[OperationalIntentReference, Query]:
        """
        Retrieve an OP Intent from the DSS, using only its ID
        Raises:
            * QueryError: if request failed, if HTTP status code is different than 200, or if the parsing of the response failed.
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
            raise QueryError(
                f"Received code {query.status_code} when attempting to retrieve operational intent reference {op_intent_id}{f'; error message: `{query.error_message}`' if query.error_message is not None else ''}",
                query,
            )
        else:
            result = query.parse_json_result(GetOperationalIntentReferenceResponse)
            return result.operational_intent_reference, query

    def get_full_op_intent(
        self,
        op_intent_ref: OperationalIntentReference,
        uss_participant_id: Optional[str] = None,
    ) -> Tuple[OperationalIntent, Query]:
        """
        Retrieve a full operational intent from its managing USS.
        Raises:
            * QueryError: if request failed, if HTTP status code is different than 200, or if the parsing of the response failed.
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
        if query.status_code != 200:
            raise QueryError(
                f"Received code {query.status_code} when attempting to retrieve operational intent details for {op_intent_ref.id}{f'; error message: `{query.error_message}`' if query.error_message is not None else ''}",
                query,
            )
        else:
            result = query.parse_json_result(GetOperationalIntentDetailsResponse)
            return result.operational_intent, query

    def get_op_intent_telemetry(
        self,
        op_intent_ref: OperationalIntentReference,
        uss_participant_id: Optional[str] = None,
    ) -> Tuple[Optional[VehicleTelemetry], Query]:
        """
        Get telemetry of an operational intent.
        Returns:
            VehicleTelemetry if available, None otherwise
        Raises:
            * QueryError: if request failed, if HTTP status code is different than 200, or if the parsing of the response failed.
        """
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
        if query.status_code == 412:
            return None, query
        elif query.status_code != 200:
            raise QueryError(
                f"Received code {query.status_code} when attempting to retrieval operational intent telemetry for {op_intent_ref.id}{f'; error message: `{query.error_message}`' if query.error_message is not None else ''}",
                query,
            )
        else:
            result = query.parse_json_result(GetOperationalIntentTelemetryResponse)
            return result.telemetry, query

    def put_op_intent(
        self,
        extents: List[Volume4D],
        key: List[EntityOVN],
        state: OperationalIntentState,
        base_url: UssBaseURL,
        oi_id: Optional[str] = None,
        ovn: Optional[str] = None,
        subscription_id: Optional[str] = None,
        force_query_scopes: Optional[Scope] = None,
    ) -> Tuple[OperationalIntentReference, List[SubscriberToNotify], Query,]:
        """
        Create or update an operational intent.

        This method will automatically add the required scopes based on the passed 'state':
          - nominal states (Accepted, Activated, Ended) require only the StrategicCoordination scope.
          - off-nominal states (Nonconforming, Contingent) require ConformanceMonitoringForSituationalAwareness

        Scenarios that wish to test the behavior of the DSS when an incorrect scope is used can force the scope
        to be with the 'force_query_scope' parameter.

        Returns:
             the operational intent reference created or updated, the subscribers to notify, the query
        Raises:
            * QueryError: if request failed, if HTTP status code is different than 200 or 201, or if the parsing of the response failed.
        """

        # Default to SCD if no override is provided
        scopes = (
            [force_query_scopes]
            if force_query_scopes
            else [Scope.StrategicCoordination]
        )

        # If no override is provided and the state warrants it, we add the CMSA scope
        if not force_query_scopes and state in [
            OperationalIntentState.Nonconforming,
            OperationalIntentState.Contingent,
        ]:
            scopes.append(Scope.ConformanceMonitoringForSituationalAwareness)

        for s in scopes:
            self._uses_scope(s)

        oi_uuid = str(uuid.uuid4()) if oi_id is None else oi_id
        create = ovn is None
        if create:
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
            subscription_id=subscription_id,
            new_subscription=ImplicitSubscriptionParameters(uss_base_url=base_url)
            if subscription_id is None
            else None,
        )
        query = query_and_describe(
            self.client,
            op.verb,
            url,
            query_type,
            self.participant_id,
            scopes=scopes,
            json=req,
        )
        if (create and query.status_code == 201) or (
            not create and query.status_code == 200
        ):
            result = query.parse_json_result(ChangeOperationalIntentReferenceResponse)
            return result.operational_intent_reference, result.subscribers, query
        elif query.status_code == 409:
            result = query.parse_json_result(AirspaceConflictResponse)
            raise QueryError(
                f"Received code 409 when attempting to {'create' if create else 'update'} operational intent with ID {oi_uuid}; error message: `{result.message}`; missing operational intent IDs: {[oi.id for oi in result.missing_operational_intents]}",
                query,
            )
        else:
            err_msg = query.error_message if query.error_message is not None else ""
            raise QueryError(
                f"Received code {query.status_code} when attempting to {'create' if create else 'update'} operational intent with ID {oi_uuid}; error message: `{err_msg}`",
                query,
            )

    def delete_op_intent(
        self,
        id: str,
        ovn: str,
    ) -> Tuple[OperationalIntentReference, List[SubscriberToNotify], Query]:
        """
        Delete an operational intent.
        Raises:
            * QueryError: if request failed, if HTTP status code is different than 200, or if the parsing of the response failed.
        """
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
            raise QueryError(
                f"Received code {query.status_code} when attempting to delete operational intent {id}{f'; error message: `{query.error_message}`' if query.error_message is not None else ''}",
                query,
            )
        else:
            result = query.parse_json_result(ChangeOperationalIntentReferenceResponse)
            return result.operational_intent_reference, result.subscribers, query

    def get_uss_availability(
        self,
        uss_id: str,
        scope: Scope = Scope.StrategicCoordination,
    ) -> Tuple[UssAvailabilityStatusResponse, Query]:
        """
        Request the availability status for the specified USS.

        By default the StrategicCoordination scope is used. It can be overridden for callers that
        wish to use a different scope.
        Raises:
            * QueryError: if request failed, if HTTP status code is different than 200, or if the parsing of the response failed.
        """
        self._uses_scope(scope)
        op = OPERATIONS[OperationID.GetUssAvailability]
        query = query_and_describe(
            self.client,
            op.verb,
            op.path.format(uss_id=uss_id),
            QueryType.F3548v21DSSGetUssAvailability,
            self.participant_id,
            scope=scope,
        )
        if query.status_code != 200:
            raise QueryError(
                f"Received code {query.status_code} when attempting to retrieve USS availability of {uss_id}{f'; error message: `{query.error_message}`' if query.error_message is not None else ''}",
                query,
            )
        else:
            result = query.parse_json_result(UssAvailabilityStatusResponse)
            return result, query

    def set_uss_availability(
        self,
        uss_id: str,
        available: Optional[bool],
        version: str = "",
    ) -> Tuple[str, Query]:
        """
        Set the availability for the USS identified by 'uss_id'.

        If 'available' is None, the availability will be set to 'Unknown'.
        True will set it to 'Normal', and False to 'Down'.

        Returns:
            A tuple composed of
            1) the new version of the USS availability;
            2) the query.
        Raises:
            * QueryError: if request failed, if HTTP status code is different than 200, or if the parsing of the response failed.
        """
        self._uses_scope(Scope.AvailabilityArbitration)
        if available is None:
            availability = UssAvailabilityState.Unknown
        elif available:
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
            raise QueryError(
                f"Received code {query.status_code} when attempting to set USS availability of {uss_id}{f'; error message: `{query.error_message}`' if query.error_message is not None else ''}",
                query,
            )
        else:
            result = query.parse_json_result(UssAvailabilityStatusResponse)
            return result.version, query

    def put_constraint_ref(
        self,
        cr_id: str,
        extents: List[Volume4D],
        uss_base_url: UssBaseURL,
        ovn: Optional[str] = None,
    ) -> Tuple[ConstraintReference, List[SubscriberToNotify], Query]:
        """
        Create or update a constraint reference.
        Returns:
            the constraint reference created or updated, the subscribers to notify, the query
        Raises:
            * QueryError if request failed, if HTTP status code is different than 200 or 201, or if the parsing of the response failed.
        """
        self._uses_scope(Scope.ConstraintManagement)
        create = ovn is None
        if create:
            op = OPERATIONS[OperationID.CreateConstraintReference]
            url = op.path.format(entityid=cr_id)
            query_type = QueryType.F3548v21DSSCreateConstraintReference
        else:
            op = OPERATIONS[OperationID.UpdateConstraintReference]
            url = op.path.format(entityid=cr_id, ovn=ovn)
            query_type = QueryType.F3548v21DSSUpdateConstraintReference

        req = PutConstraintReferenceParameters(
            extents=extents,
            uss_base_url=uss_base_url,
        )
        query = query_and_describe(
            self.client,
            op.verb,
            url,
            query_type,
            self.participant_id,
            scope=Scope.ConstraintManagement,
            json=req,
        )
        if (create and query.status_code == 201) or (
            not create and query.status_code == 200
        ):
            result = query.parse_json_result(ChangeConstraintReferenceResponse)
            return result.constraint_reference, result.subscribers, query
        else:
            err_msg = query.error_message if query.error_message is not None else ""
            raise QueryError(
                f"Received code {query.status_code} when attempting to {'create' if create else 'update'} constraint reference with ID {cr_id}; error message: `{err_msg}`",
                query,
            )

    def get_constraint_ref(self, id: str) -> Tuple[ConstraintReference, Query]:
        """
        Retrieve a constraint reference from the DSS, using only its ID
        Raises:
            * QueryError: if request failed, if HTTP status code is different than 200, or if the parsing of the response failed.
        """
        self._uses_scope(Scope.ConstraintManagement)
        op = OPERATIONS[OperationID.GetConstraintReference]
        query = query_and_describe(
            self.client,
            op.verb,
            op.path.format(entityid=id),
            QueryType.F3548v21DSSGetConstraintReference,
            self.participant_id,
            scope=Scope.ConstraintManagement,
        )
        if query.status_code != 200:
            raise QueryError(
                f"Received code {query.status_code} when attempting to retrieve constraint reference {id}{f'; error message: `{query.error_message}`' if query.error_message is not None else ''}",
                query,
            )
        else:
            result = query.parse_json_result(ChangeConstraintReferenceResponse)
            return result.constraint_reference, query

    def find_constraint_ref(
        self, extent: Volume4D
    ) -> Tuple[List[ConstraintReference], Query]:
        """
        Find constraint references overlapping with a given volume 4D.
        Raises:
            * QueryError: if request failed, if HTTP status code is different than 200, or if the parsing of the response failed.
        """
        self._uses_scope(Scope.ConstraintManagement)
        op = OPERATIONS[OperationID.QueryConstraintReferences]
        req = QueryConstraintReferenceParameters(area_of_interest=extent)
        query = query_and_describe(
            self.client,
            op.verb,
            op.path,
            QueryType.F3548v21DSSQueryConstraintReferences,
            self.participant_id,
            scope=Scope.ConstraintManagement,
            json=req,
        )
        if query.status_code != 200:
            raise QueryError(
                f"Received code {query.status_code} when attempting to find operational intents in {extent}{f'; error message: `{query.error_message}`' if query.error_message is not None else ''}",
                query,
            )
        else:
            result = query.parse_json_result(QueryConstraintReferencesResponse)
            return result.constraint_references, query

    def delete_constraint_ref(
        self,
        id: str,
        ovn: str,
    ) -> Tuple[ConstraintReference, List[SubscriberToNotify], Query]:
        """
        Delete a constraint reference.
        Raises:
            * QueryError: if request failed, if HTTP status code is different than 200, or if the parsing of the response failed.
        """
        self._uses_scope(Scope.ConstraintManagement)
        op = OPERATIONS[OperationID.DeleteConstraintReference]
        query = query_and_describe(
            self.client,
            op.verb,
            op.path.format(entityid=id, ovn=ovn),
            QueryType.F3548v21DSSDeleteConstraintReference,
            self.participant_id,
            scope=Scope.ConstraintManagement,
        )
        if query.status_code != 200:
            raise QueryError(
                f"Received code {query.status_code} when attempting to delete constraint reference {id}{f'; error message: `{query.error_message}`' if query.error_message is not None else ''}",
                query,
            )
        else:
            result = query.parse_json_result(ChangeConstraintReferenceResponse)
            return result.constraint_reference, result.subscribers, query

    def make_report(
        self,
        exchange: ExchangeRecord,
    ) -> Tuple[Optional[str], Query]:
        """
        Make a DSS report.
        Returns:
            A tuple composed of
            1) the report ID;
            2) the query.
        Raises:
            * QueryError: if request failed, if HTTP status code is different than 201, or if the parsing of the response failed.
        """
        use_scope = self._uses_any_scope(
            Scope.ConstraintManagement,
            Scope.ConstraintProcessing,
            Scope.StrategicCoordination,
            Scope.ConformanceMonitoringForSituationalAwareness,
            Scope.AvailabilityArbitration,
        )

        req = ErrorReport(exchange=exchange)
        op = OPERATIONS[OperationID.MakeDssReport]
        query = query_and_describe(
            self.client,
            op.verb,
            op.path,
            QueryType.F3548v21DSSMakeDssReport,
            self.participant_id,
            scope=use_scope,
            json=req,
        )

        if query.status_code != 201:
            raise QueryError(
                f"Received code {query.status_code} when attempting to make DSS report{f'; error message: `{query.error_message}`' if query.error_message is not None else ''}",
                query,
            )
        else:
            result = query.parse_json_result(ErrorReport)
            return result.report_id, query

    def query_subscriptions(
        self,
        volume: Volume4D,
    ) -> FetchedSubscriptions:
        """Returns any subscription owned by the caller in the specified 4D volume."""
        self._uses_scope(Scope.StrategicCoordination)
        return fetch.query_subscriptions(
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

    def get_authorized_scopes(self) -> Set[str]:
        return self._auth_adapter.scopes.copy()

    @property
    def participant_id(self) -> str:
        return self._specification.participant_id

    @property
    def base_url(self) -> str:
        return self._specification.base_url

    def get_authorized_scope_not_in(self, ignored_scopes: List[str]) -> Optional[str]:
        """Returns a scope that this DSS Resource is allowed to use but that is not any of the ones that are passed
        in 'ignored_scopes'. If no such scope is found, None is returned.

        This function is mostly meant to be used from scenarios that are testing authentication and authorization of endpoints.

        The output of this function is deterministic.
        """
        available_scopes_scd = self.get_authorized_scopes()
        for to_ignore in ignored_scopes:
            available_scopes_scd.discard(to_ignore)

        if len(available_scopes_scd) > 0:
            return sorted(available_scopes_scd)[0]

        return None

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
            self._specification.user_participant_ids
            if "user_participant_ids" in self._specification
            and self._specification.user_participant_ids
            else [],
            self._specification.base_url,
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
