import datetime
from typing import Dict, List, Optional, Union, Set

from implicitdict import ImplicitDict
import s2sphere
from uas_standards import Operation

from monitoring.monitorlib.fetch.rid import RIDQuery, Subscription, ISA
from monitoring.monitorlib.rid import RIDVersion
from uas_standards.astm.f3411 import v19, v22a
import uas_standards.astm.f3411.v19.api
import uas_standards.astm.f3411.v19.constants
import uas_standards.astm.f3411.v22a.api
import uas_standards.astm.f3411.v22a.constants
import yaml
from yaml.representer import Representer

from monitoring.monitorlib import (
    fetch,
    infrastructure,
    rid_v1,
    rid_v2,
)


class ChangedSubscription(RIDQuery):
    """Version-independent representation of a subscription following a change in the DSS."""

    mutation: Optional[str] = None

    @property
    def _v19_response(self) -> v19.api.PutSubscriptionResponse:
        return ImplicitDict.parse(
            self.v19_query.response.json,
            v19.api.PutSubscriptionResponse,
        )

    @property
    def _v22a_response(self) -> v22a.api.PutSubscriptionResponse:
        return ImplicitDict.parse(
            self.v22a_query.response.json,
            v22a.api.PutSubscriptionResponse,
        )

    @property
    def errors(self) -> List[str]:
        if self.status_code != 200:
            return ["Failed to mutate subscription ({})".format(self.status_code)]
        if self.query.response.json is None:
            return ["Subscription response did not include valid JSON"]

        if self.rid_version == RIDVersion.f3411_19:
            try:
                value = self._v19_response
                if not value:
                    return ["Unknown error with F3411-19 PutSubscriptionResponse"]
            except ValueError as e:
                return [f"Error parsing F3411-19 USS PutSubscriptionResponse: {str(e)}"]

        if self.rid_version == RIDVersion.f3411_22a:
            try:
                value = self._v22a_response
                if not value:
                    return ["Unknown error with F3411-22a PutSubscriptionResponse"]
            except ValueError as e:
                return [
                    f"Error parsing F3411-22a USS PutSubscriptionResponse: {str(e)}"
                ]

        return []

    @property
    def subscription(self) -> Optional[Subscription]:
        if not self.success:
            return None
        if self.rid_version == RIDVersion.f3411_19:
            return Subscription(v19_value=self._v19_response.subscription)
        elif self.rid_version == RIDVersion.f3411_22a:
            return Subscription(v22a_value=self._v22a_response.subscription)
        else:
            raise NotImplementedError(
                f"Cannot retrieve subscription using RID version {self.rid_version}"
            )

    @property
    def isas(self) -> List[ISA]:
        if self.rid_version == RIDVersion.f3411_19:
            return [ISA(v19_value=isa) for isa in self._v19_response.service_areas]
        elif self.rid_version == RIDVersion.f3411_22a:
            return [ISA(v22a_value=isa) for isa in self._v22a_response.service_areas]
        else:
            raise NotImplementedError(
                f"Cannot retrieve ISAs using RID version {self.rid_version}"
            )


def upsert_subscription(
    area_vertices: List[s2sphere.LatLng],
    alt_lo: float,
    alt_hi: float,
    start_time: Optional[datetime.datetime],
    end_time: Optional[datetime.datetime],
    uss_base_url: str,
    subscription_id: str,
    rid_version: RIDVersion,
    utm_client: infrastructure.UTMClientSession,
    subscription_version: Optional[str] = None,
    participant_id: Optional[str] = None,
) -> ChangedSubscription:
    mutation = "create" if subscription_version is None else "update"
    if rid_version == RIDVersion.f3411_19:
        body = {
            "extents": rid_v1.make_volume_4d(
                area_vertices,
                alt_lo,
                alt_hi,
                start_time,
                end_time,
            ),
            "callbacks": {
                "identification_service_area_url": uss_base_url
                + v19.api.OPERATIONS[
                    v19.api.OperationID.PostIdentificationServiceArea
                ].path[: -len("/{id}")]
            },
        }
        if subscription_version is None:
            op = v19.api.OPERATIONS[v19.api.OperationID.CreateSubscription]
            url = op.path.format(id=subscription_id)
        else:
            op = v19.api.OPERATIONS[v19.api.OperationID.UpdateSubscription]
            url = op.path.format(id=subscription_id, version=subscription_version)
        return ChangedSubscription(
            mutation=mutation,
            v19_query=fetch.query_and_describe(
                utm_client,
                op.verb,
                url,
                json=body,
                scope=v19.constants.Scope.Read,
                participant_id=participant_id,
            ),
        )
    elif rid_version == RIDVersion.f3411_22a:
        body = {
            "extents": rid_v2.make_volume_4d(
                area_vertices,
                alt_lo,
                alt_hi,
                start_time,
                end_time,
            ),
            "uss_base_url": uss_base_url,
        }
        if subscription_version is None:
            op = v22a.api.OPERATIONS[v22a.api.OperationID.CreateSubscription]
            url = op.path.format(id=subscription_id)
        else:
            op = v22a.api.OPERATIONS[v22a.api.OperationID.UpdateSubscription]
            url = op.path.format(id=subscription_id, version=subscription_version)
        return ChangedSubscription(
            mutation=mutation,
            v22a_query=fetch.query_and_describe(
                utm_client,
                op.verb,
                url,
                json=body,
                scope=v22a.constants.Scope.DisplayProvider,
                participant_id=participant_id,
            ),
        )
    else:
        raise NotImplementedError(
            f"Cannot upsert subscription using RID version {rid_version}"
        )


def delete_subscription(
    subscription_id: str,
    subscription_version: str,
    rid_version: RIDVersion,
    utm_client: infrastructure.UTMClientSession,
    participant_id: Optional[str] = None,
) -> ChangedSubscription:
    if rid_version == RIDVersion.f3411_19:
        op = v19.api.OPERATIONS[v19.api.OperationID.DeleteSubscription]
        url = op.path.format(id=subscription_id, version=subscription_version)
        return ChangedSubscription(
            mutation="delete",
            v19_query=fetch.query_and_describe(
                utm_client,
                op.verb,
                url,
                scope=v19.constants.Scope.Read,
                participant_id=participant_id,
            ),
        )
    elif rid_version == RIDVersion.f3411_22a:
        op = v22a.api.OPERATIONS[v22a.api.OperationID.DeleteSubscription]
        url = op.path.format(id=subscription_id, version=subscription_version)
        return ChangedSubscription(
            mutation="delete",
            v22a_query=fetch.query_and_describe(
                utm_client,
                op.verb,
                url,
                scope=v22a.constants.Scope.DisplayProvider,
                participant_id=participant_id,
            ),
        )
    else:
        raise NotImplementedError(
            f"Cannot delete subscription using RID version {rid_version}"
        )


class ISAChangeNotification(RIDQuery):
    """Version-independent representation of response to a USS notification following an ISA change in the DSS."""

    @property
    def errors(self) -> List[str]:
        # Tolerate not-strictly-correct 200 response
        if self.status_code != 204 and self.status_code != 200:
            return ["Failed to notify ({})".format(self.status_code)]
        return []


class SubscriberToNotify(ImplicitDict):
    """Version-independent representation of a subscriber to notify of a change in the DSS."""

    v19_value: Optional[v19.api.SubscriberToNotify] = None
    v22a_value: Optional[v22a.api.SubscriberToNotify] = None

    @property
    def rid_version(self) -> RIDVersion:
        if self.v19_value is not None:
            return RIDVersion.f3411_19
        elif self.v22a_value is not None:
            return RIDVersion.f3411_22a
        else:
            raise ValueError(
                "No valid representation was specified for SubscriberToNotify"
            )

    @property
    def raw(
        self,
    ) -> Union[v19.api.SubscriberToNotify, v22a.api.SubscriberToNotify]:
        if self.rid_version == RIDVersion.f3411_19:
            return self.v19_value
        elif self.rid_version == RIDVersion.f3411_22a:
            return self.v22a_value
        else:
            raise NotImplementedError(
                f"Cannot retrieve raw subscriber to notify using RID version {self.rid_version}"
            )

    def notify(
        self,
        isa_id: str,
        utm_session: infrastructure.UTMClientSession,
        isa: Optional[ISA] = None,
        participant_id: Optional[str] = None,
    ) -> ISAChangeNotification:
        # Note that optional `extents` are not specified
        if self.rid_version == RIDVersion.f3411_19:
            body = {
                "subscriptions": self.v19_value.subscriptions,
            }
            if isa is not None:
                body["service_area"] = isa.as_v19()
            url = self.v19_value.url + "/" + isa_id
            return ISAChangeNotification(
                v19_query=fetch.query_and_describe(
                    utm_session,
                    "POST",
                    url,
                    json=body,
                    scope=v19.constants.Scope.Write,
                    participant_id=participant_id,
                )
            )
        elif self.rid_version == RIDVersion.f3411_22a:
            body = {
                "subscriptions": self.v22a_value.subscriptions,
            }
            if isa is not None:
                body["service_area"] = isa.as_v22a()
            op = v22a.api.OPERATIONS[v22a.api.OperationID.PostIdentificationServiceArea]
            url = self.v22a_value.url + op.path.format(id=isa_id)
            return ISAChangeNotification(
                v22a_query=fetch.query_and_describe(
                    utm_session,
                    op.verb,
                    url,
                    json=body,
                    scope=v22a.constants.Scope.ServiceProvider,
                    participant_id=participant_id,
                )
            )
        else:
            raise NotImplementedError(
                f"Cannot notify subscriber using RID version {self.rid_version}"
            )

    @property
    def url(self) -> str:
        return self.raw.url


class ChangedISA(RIDQuery):
    """Version-independent representation of a changed F3411 identification service area."""

    mutation: Optional[str] = None

    @property
    def _v19_response(
        self,
    ) -> v19.api.PutIdentificationServiceAreaResponse:
        return ImplicitDict.parse(
            self.v19_query.response.json,
            v19.api.PutIdentificationServiceAreaResponse,
        )

    @property
    def _v22a_response(
        self,
    ) -> v22a.api.PutIdentificationServiceAreaResponse:
        return ImplicitDict.parse(
            self.v22a_query.response.json,
            v22a.api.PutIdentificationServiceAreaResponse,
        )

    @property
    def errors(self) -> List[str]:
        # Tolerate reasonable-but-technically-incorrect code 201
        if not (
            self.status_code == 200
            or (self.mutation == "create" and self.status_code == 201)
        ):
            return ["Failed to mutate ISA ({})".format(self.status_code)]
        if self.query.response.json is None:
            return ["ISA response did not include valid JSON"]

        if self.rid_version == RIDVersion.f3411_19:
            try:
                value = self._v19_response
                if not value:
                    return [
                        "Unknown error with F3411-19 PutIdentificationServiceAreaResponse"
                    ]
            except ValueError as e:
                return [
                    f"Error parsing F3411-19 USS PutIdentificationServiceAreaResponse: {str(e)}"
                ]

        if self.rid_version == RIDVersion.f3411_22a:
            try:
                value = self._v22a_response
                if not value:
                    return [
                        "Unknown error with F3411-22a PutIdentificationServiceAreaResponse"
                    ]
            except ValueError as e:
                return [
                    f"Error parsing F3411-22a USS PutIdentificationServiceAreaResponse: {str(e)}"
                ]

        return []

    @property
    def isa(self) -> ISA:
        if self.rid_version == RIDVersion.f3411_19:
            return ISA(v19_value=self._v19_response.service_area)
        elif self.rid_version == RIDVersion.f3411_22a:
            return ISA(v22a_value=self._v22a_response.service_area)
        else:
            raise NotImplementedError(
                f"Cannot retrieve ISA using RID version {self.rid_version}"
            )

    @property
    def subscribers(self) -> Optional[List[SubscriberToNotify]]:
        if self.rid_version == RIDVersion.f3411_19:
            if (
                "subscribers" not in self._v19_response
                or self._v19_response.subscribers is None
            ):
                return None
            return [
                SubscriberToNotify(v19_value=sub)
                for sub in self._v19_response.subscribers
            ]
        elif self.rid_version == RIDVersion.f3411_22a:
            return (
                [
                    SubscriberToNotify(v22a_value=sub)
                    for sub in self._v22a_response.subscribers
                ]
                if "subscribers" in self._v22a_response
                else []
            )
        else:
            raise NotImplementedError(
                f"Cannot retrieve subscribers to notify using RID version {self.rid_version}"
            )

    @property
    def sub_ids(self) -> Set[str]:
        if self.rid_version == RIDVersion.f3411_19:
            return set(
                [
                    subscription.subscription_id
                    for subscriber in self._v19_response.subscribers
                    for subscription in subscriber.subscriptions
                    if subscription.subscription_id is not None
                ]
            )
        elif self.rid_version == RIDVersion.f3411_22a:
            return set(
                [
                    subscription.subscription_id
                    for subscriber in self._v22a_response.subscribers
                    if subscriber is not None
                    for subscription in subscriber.subscriptions
                ]
            )
        else:
            raise NotImplementedError(
                f"Cannot retrieve subscription ids using RID version {self.rid_version}"
            )


class ISAChange(ImplicitDict):
    """Result of an attempt to change an ISA (including DSS & notifications)"""

    dss_query: ChangedISA

    notifications: Dict[str, ISAChangeNotification]
    """Mapping from USS base URL to change notification query"""


def build_isa_request_body(
    area_vertices: List[s2sphere.LatLng],
    alt_lo: float,
    alt_hi: float,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    uss_base_url: str,
    rid_version: RIDVersion,
) -> Dict[str, any]:
    """Build the http request body expected to PUT or UPDATE an ISA on a DSS,
    in accordance with the specified rid_version."""
    if rid_version == RIDVersion.f3411_19:
        return {
            "extents": rid_v1.make_volume_4d(
                area_vertices,
                alt_lo,
                alt_hi,
                start_time,
                end_time,
            ),
            "flights_url": uss_base_url
            + v19.api.OPERATIONS[v19.api.OperationID.SearchFlights].path,
        }
    elif rid_version == RIDVersion.f3411_22a:
        return {
            "extents": rid_v2.make_volume_4d(
                area_vertices,
                alt_lo,
                alt_hi,
                start_time,
                end_time,
            ),
            "uss_base_url": uss_base_url,
        }
    else:
        raise NotImplementedError(
            f"Cannot build ISA payload for RID version {rid_version}"
        )


def build_isa_url(
    rid_version: RIDVersion, isa_id: str, isa_version: Optional[str] = None
) -> (Operation, str):
    """Build the required URL to create, get, update or delete an ISA on a DSS,
    in accordance with the specified rid_version and isa_version, if it is available.

    Note that for mutations and deletions, isa_version must be provided.
    """
    if rid_version == RIDVersion.f3411_19:
        if isa_version is None:
            op = v19.api.OPERATIONS[v19.api.OperationID.CreateIdentificationServiceArea]
            return (op, op.path.format(id=isa_id))
        else:
            op = v19.api.OPERATIONS[v19.api.OperationID.UpdateIdentificationServiceArea]
            return (op, op.path.format(id=isa_id, version=isa_version))
    elif rid_version == RIDVersion.f3411_22a:
        if isa_version is None:
            op = v22a.api.OPERATIONS[
                v22a.api.OperationID.CreateIdentificationServiceArea
            ]
            return (op, op.path.format(id=isa_id))
        else:
            op = v22a.api.OPERATIONS[
                v22a.api.OperationID.UpdateIdentificationServiceArea
            ]
            return (op, op.path.format(id=isa_id, version=isa_version))
    else:
        raise NotImplementedError(f"Cannot build ISA URL for RID version {rid_version}")


def put_isa(
    area_vertices: List[s2sphere.LatLng],
    alt_lo: float,
    alt_hi: float,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    uss_base_url: str,
    isa_id: str,
    rid_version: RIDVersion,
    utm_client: infrastructure.UTMClientSession,
    isa_version: Optional[str] = None,
    participant_id: Optional[str] = None,
) -> ISAChange:
    mutation = "create" if isa_version is None else "update"
    body = build_isa_request_body(
        area_vertices,
        alt_lo,
        alt_hi,
        start_time,
        end_time,
        uss_base_url,
        rid_version,
    )
    (op, url) = build_isa_url(rid_version, isa_id, isa_version)
    if rid_version == RIDVersion.f3411_19:
        dss_response = ChangedISA(
            mutation=mutation,
            v19_query=fetch.query_and_describe(
                utm_client,
                op.verb,
                url,
                json=body,
                scope=v19.constants.Scope.Write,
                participant_id=participant_id,
            ),
        )
    elif rid_version == RIDVersion.f3411_22a:
        dss_response = ChangedISA(
            mutation=mutation,
            v22a_query=fetch.query_and_describe(
                utm_client,
                op.verb,
                url,
                json=body,
                scope=v22a.constants.Scope.ServiceProvider,
                participant_id=participant_id,
            ),
        )
    else:
        raise NotImplementedError(f"Cannot upsert ISA using RID version {rid_version}")

    if dss_response.success:
        isa = dss_response.isa
        notifications = {
            sub.url: sub.notify(isa.id, utm_client, isa)
            for sub in dss_response.subscribers
        }
    else:
        notifications = {}

    return ISAChange(dss_query=dss_response, notifications=notifications)


def delete_isa(
    isa_id: str,
    isa_version: str,
    rid_version: RIDVersion,
    utm_client: infrastructure.UTMClientSession,
    participant_id: Optional[str] = None,
) -> ISAChange:
    if rid_version == RIDVersion.f3411_19:
        op = v19.api.OPERATIONS[v19.api.OperationID.DeleteIdentificationServiceArea]
        url = op.path.format(id=isa_id, version=isa_version)
        dss_response = ChangedISA(
            mutation="delete",
            v19_query=fetch.query_and_describe(
                utm_client,
                op.verb,
                url,
                scope=v19.constants.Scope.Write,
                participant_id=participant_id,
            ),
        )
    elif rid_version == RIDVersion.f3411_22a:
        op = v22a.api.OPERATIONS[v22a.api.OperationID.DeleteIdentificationServiceArea]
        url = op.path.format(id=isa_id, version=isa_version)
        dss_response = ChangedISA(
            mutation="delete",
            v22a_query=fetch.query_and_describe(
                utm_client,
                op.verb,
                url,
                scope=v22a.constants.Scope.ServiceProvider,
                participant_id=participant_id,
            ),
        )
    else:
        raise NotImplementedError(f"Cannot delete ISA using RID version {rid_version}")

    if dss_response.success:
        isa = dss_response.isa
        notifications = {
            sub.url: sub.notify(isa.id, utm_client) for sub in dss_response.subscribers
        }
    else:
        notifications = {}

    return ISAChange(dss_query=dss_response, notifications=notifications)


yaml.add_representer(ChangedSubscription, Representer.represent_dict)
yaml.add_representer(ChangedISA, Representer.represent_dict)
yaml.add_representer(ISAChange, Representer.represent_dict)
