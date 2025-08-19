import datetime

import s2sphere
import uas_standards.astm.f3411.v19.api as v19_api
import uas_standards.astm.f3411.v19.constants as v19_constants
import uas_standards.astm.f3411.v22a.api as v22a_api
import uas_standards.astm.f3411.v22a.constants as v22a_constants
import yaml
from implicitdict import ImplicitDict
from uas_standards import Operation
from yaml.representer import Representer

from monitoring.monitorlib import fetch, infrastructure, rid_v1, rid_v2
from monitoring.monitorlib.fetch import QueryType
from monitoring.monitorlib.fetch.rid import ISA, RIDQuery, Subscription
from monitoring.monitorlib.rid import RIDVersion


class ChangedSubscription(RIDQuery):
    """Version-independent representation of a subscription following a change in the DSS."""

    mutation: str | None = None

    @property
    def _v19_response(self) -> v19_api.PutSubscriptionResponse:
        return ImplicitDict.parse(
            self.v19_query.response.json,
            v19_api.PutSubscriptionResponse,
        )

    @property
    def _v22a_response(self) -> v22a_api.PutSubscriptionResponse:
        return ImplicitDict.parse(
            self.v22a_query.response.json,
            v22a_api.PutSubscriptionResponse,
        )

    @property
    def errors(self) -> list[str]:
        if self.status_code != 200:
            return [f"Failed to mutate subscription ({self.status_code})"]
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
    def subscription(self) -> Subscription | None:
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
    def isas(self) -> list[ISA]:
        if self.rid_version == RIDVersion.f3411_19:
            return [ISA(v19_value=isa) for isa in self._v19_response.service_areas]
        elif self.rid_version == RIDVersion.f3411_22a:
            return [ISA(v22a_value=isa) for isa in self._v22a_response.service_areas]
        else:
            raise NotImplementedError(
                f"Cannot retrieve ISAs using RID version {self.rid_version}"
            )


def upsert_subscription(
    area_vertices: list[s2sphere.LatLng],
    alt_lo: float,
    alt_hi: float,
    start_time: datetime.datetime | None,
    end_time: datetime.datetime | None,
    uss_base_url: str,
    subscription_id: str,
    rid_version: RIDVersion,
    utm_client: infrastructure.UTMClientSession,
    subscription_version: str | None = None,
    participant_id: str | None = None,
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
                + v19_api.OPERATIONS[
                    v19_api.OperationID.PostIdentificationServiceArea
                ].path[: -len("/{id}")]
            },
        }
        if subscription_version is None:
            op = v19_api.OPERATIONS[v19_api.OperationID.CreateSubscription]
            url = op.path.format(id=subscription_id)
            query_type = QueryType.F3411v19DSSCreateSubscription
        else:
            op = v19_api.OPERATIONS[v19_api.OperationID.UpdateSubscription]
            url = op.path.format(id=subscription_id, version=subscription_version)
            query_type = QueryType.F3411v19DSSUpdateSubscription
        return ChangedSubscription(
            mutation=mutation,
            v19_query=fetch.query_and_describe(
                utm_client,
                op.verb,
                url,
                json=body,
                scope=v19_constants.Scope.Read,
                participant_id=participant_id,
                query_type=query_type,
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
            op = v22a_api.OPERATIONS[v22a_api.OperationID.CreateSubscription]
            url = op.path.format(id=subscription_id)
            query_type = QueryType.F3411v22aDSSCreateSubscription
        else:
            op = v22a_api.OPERATIONS[v22a_api.OperationID.UpdateSubscription]
            url = op.path.format(id=subscription_id, version=subscription_version)
            query_type = QueryType.F3411v22aDSSUpdateSubscription
        return ChangedSubscription(
            mutation=mutation,
            v22a_query=fetch.query_and_describe(
                utm_client,
                op.verb,
                url,
                json=body,
                scope=v22a_constants.Scope.DisplayProvider,
                participant_id=participant_id,
                query_type=query_type,
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
    participant_id: str | None = None,
) -> ChangedSubscription:
    if rid_version == RIDVersion.f3411_19:
        op = v19_api.OPERATIONS[v19_api.OperationID.DeleteSubscription]
        url = op.path.format(id=subscription_id, version=subscription_version)
        return ChangedSubscription(
            mutation="delete",
            v19_query=fetch.query_and_describe(
                utm_client,
                op.verb,
                url,
                scope=v19_constants.Scope.Read,
                participant_id=participant_id,
                query_type=QueryType.F3411v19DSSDeleteSubscription,
            ),
        )
    elif rid_version == RIDVersion.f3411_22a:
        op = v22a_api.OPERATIONS[v22a_api.OperationID.DeleteSubscription]
        url = op.path.format(id=subscription_id, version=subscription_version)
        return ChangedSubscription(
            mutation="delete",
            v22a_query=fetch.query_and_describe(
                utm_client,
                op.verb,
                url,
                scope=v22a_constants.Scope.DisplayProvider,
                participant_id=participant_id,
                query_type=QueryType.F3411v22aDSSDeleteSubscription,
            ),
        )
    else:
        raise NotImplementedError(
            f"Cannot delete subscription using RID version {rid_version}"
        )


class ISAChangeNotification(RIDQuery):
    """Version-independent representation of response to a USS notification following an ISA change in the DSS."""

    @property
    def errors(self) -> list[str]:
        # Tolerate not-strictly-correct 200 response
        if self.status_code != 204 and self.status_code != 200:
            return [f"Failed to notify ({self.status_code})"]
        return []


class SubscriberToNotify(ImplicitDict):
    """Version-independent representation of a subscriber to notify of a change in the DSS."""

    v19_value: v19_api.SubscriberToNotify | None = None
    v22a_value: v22a_api.SubscriberToNotify | None = None

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
    ) -> v19_api.SubscriberToNotify | v22a_api.SubscriberToNotify:
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
        isa: ISA | None = None,
        participant_id: str | None = None,
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
                    scope=v19_constants.Scope.Write,
                    participant_id=participant_id,
                    query_type=QueryType.F3411v19USSPostIdentificationServiceArea,
                )
            )
        elif self.rid_version == RIDVersion.f3411_22a:
            body = {
                "subscriptions": self.v22a_value.subscriptions,
            }
            if isa is not None:
                body["service_area"] = isa.as_v22a()
            op = v22a_api.OPERATIONS[v22a_api.OperationID.PostIdentificationServiceArea]
            url = self.v22a_value.url + op.path.format(id=isa_id)
            return ISAChangeNotification(
                v22a_query=fetch.query_and_describe(
                    utm_session,
                    op.verb,
                    url,
                    json=body,
                    scope=v22a_constants.Scope.ServiceProvider,
                    participant_id=participant_id,
                    query_type=QueryType.F3411v22aUSSPostIdentificationServiceArea,
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

    mutation: str | None = None

    @property
    def _v19_response(
        self,
    ) -> v19_api.PutIdentificationServiceAreaResponse:
        return ImplicitDict.parse(
            self.v19_query.response.json,
            v19_api.PutIdentificationServiceAreaResponse,
        )

    @property
    def _v22a_response(
        self,
    ) -> v22a_api.PutIdentificationServiceAreaResponse:
        return ImplicitDict.parse(
            self.v22a_query.response.json,
            v22a_api.PutIdentificationServiceAreaResponse,
        )

    @property
    def errors(self) -> list[str]:
        # Tolerate reasonable-but-technically-incorrect code 201
        if not (
            self.status_code == 200
            or (self.mutation == "create" and self.status_code == 201)
        ):
            return [f"Failed to mutate ISA ({self.status_code})"]
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
    def subscribers(self) -> list[SubscriberToNotify] | None:
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
    def sub_ids(self) -> set[str]:
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

    notifications: dict[str, ISAChangeNotification]
    """Mapping from USS base URL to change notification query"""

    @property
    def subscribers(self) -> list[SubscriberToNotify] | None:
        """List of subscribers that required a notification for the change."""
        return self.dss_query.subscribers


def build_isa_request_body(
    area_vertices: list[s2sphere.LatLng],
    alt_lo: float,
    alt_hi: float,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    uss_base_url: str,
    rid_version: RIDVersion,
) -> dict[str, any]:
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
            + v19_api.OPERATIONS[v19_api.OperationID.SearchFlights].path,
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
    rid_version: RIDVersion, isa_id: str, isa_version: str | None = None
) -> (Operation, str):
    """Build the required URL to create, get, update or delete an ISA on a DSS,
    in accordance with the specified rid_version and isa_version, if it is available.

    Note that for mutations and deletions, isa_version must be provided.
    """
    if rid_version == RIDVersion.f3411_19:
        if isa_version is None:
            op = v19_api.OPERATIONS[v19_api.OperationID.CreateIdentificationServiceArea]
            return (op, op.path.format(id=isa_id))
        else:
            op = v19_api.OPERATIONS[v19_api.OperationID.UpdateIdentificationServiceArea]
            return (op, op.path.format(id=isa_id, version=isa_version))
    elif rid_version == RIDVersion.f3411_22a:
        if isa_version is None:
            op = v22a_api.OPERATIONS[
                v22a_api.OperationID.CreateIdentificationServiceArea
            ]
            return (op, op.path.format(id=isa_id))
        else:
            op = v22a_api.OPERATIONS[
                v22a_api.OperationID.UpdateIdentificationServiceArea
            ]
            return (op, op.path.format(id=isa_id, version=isa_version))
    else:
        raise NotImplementedError(f"Cannot build ISA URL for RID version {rid_version}")


def put_isa(
    area_vertices: list[s2sphere.LatLng],
    alt_lo: float,
    alt_hi: float,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    uss_base_url: str,
    isa_id: str,
    rid_version: RIDVersion,
    utm_client: infrastructure.UTMClientSession,
    isa_version: str | None = None,
    participant_id: str | None = None,
    do_not_notify: str | list[str] | None = None,
) -> ISAChange:
    is_creation = isa_version is None
    mutation = "create" if is_creation else "update"
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
        query_type = (
            QueryType.F3411v19DSSUpdateIdentificationServiceArea
            if is_creation
            else QueryType.F3411v19DSSCreateIdentificationServiceArea
        )
        dss_response = ChangedISA(
            mutation=mutation,
            v19_query=fetch.query_and_describe(
                utm_client,
                op.verb,
                url,
                json=body,
                scope=v19_constants.Scope.Write,
                participant_id=participant_id,
                query_type=query_type,
            ),
        )
    elif rid_version == RIDVersion.f3411_22a:
        query_type = (
            QueryType.F3411v22aDSSUpdateIdentificationServiceArea
            if is_creation
            else QueryType.F3411v22aDSSCreateIdentificationServiceArea
        )
        dss_response = ChangedISA(
            mutation=mutation,
            v22a_query=fetch.query_and_describe(
                utm_client,
                op.verb,
                url,
                json=body,
                scope=v22a_constants.Scope.ServiceProvider,
                participant_id=participant_id,
                query_type=query_type,
            ),
        )
    else:
        raise NotImplementedError(f"Cannot upsert ISA using RID version {rid_version}")

    if dss_response.success:
        isa = dss_response.isa
        if isinstance(do_not_notify, str):
            do_not_notify = [do_not_notify]
        elif do_not_notify is None:
            do_not_notify = []
        notifications = {
            sub.url: sub.notify(isa.id, utm_client, isa)
            for sub in dss_response.subscribers
            if not any(sub.url.startswith(base_url) for base_url in do_not_notify)
        }
    else:
        notifications = {}

    return ISAChange(dss_query=dss_response, notifications=notifications)


def delete_isa(
    isa_id: str,
    isa_version: str,
    rid_version: RIDVersion,
    utm_client: infrastructure.UTMClientSession,
    participant_id: str | None = None,
    do_not_notify: str | list[str] | None = None,
) -> ISAChange:
    if rid_version == RIDVersion.f3411_19:
        op = v19_api.OPERATIONS[v19_api.OperationID.DeleteIdentificationServiceArea]
        url = op.path.format(id=isa_id, version=isa_version)
        dss_response = ChangedISA(
            mutation="delete",
            v19_query=fetch.query_and_describe(
                utm_client,
                op.verb,
                url,
                scope=v19_constants.Scope.Write,
                participant_id=participant_id,
                query_type=QueryType.F3411v19DSSDeleteIdentificationServiceArea,
            ),
        )
    elif rid_version == RIDVersion.f3411_22a:
        op = v22a_api.OPERATIONS[v22a_api.OperationID.DeleteIdentificationServiceArea]
        url = op.path.format(id=isa_id, version=isa_version)
        dss_response = ChangedISA(
            mutation="delete",
            v22a_query=fetch.query_and_describe(
                utm_client,
                op.verb,
                url,
                scope=v22a_constants.Scope.ServiceProvider,
                participant_id=participant_id,
                query_type=QueryType.F3411v22aDSSDeleteIdentificationServiceArea,
            ),
        )
    else:
        raise NotImplementedError(f"Cannot delete ISA using RID version {rid_version}")

    if dss_response.success:
        isa = dss_response.isa
        if isinstance(do_not_notify, str):
            do_not_notify = [do_not_notify]
        elif do_not_notify is None:
            do_not_notify = []
        notifications = {
            sub.url: sub.notify(isa.id, utm_client)
            for sub in dss_response.subscribers
            if not any(sub.url.startswith(base_url) for base_url in do_not_notify)
        }
    else:
        notifications = {}

    return ISAChange(dss_query=dss_response, notifications=notifications)


class UpdatedISA(RIDQuery):
    """Version-independent representation of an updated (via notification) F3411 identification service area."""

    @property
    def _v19_request(
        self,
    ) -> v19_api.PutIdentificationServiceAreaNotificationParameters:
        return ImplicitDict.parse(
            self.v19_query.request.json,
            v19_api.PutIdentificationServiceAreaNotificationParameters,
        )

    @property
    def _v22a_request(
        self,
    ) -> v22a_api.PutIdentificationServiceAreaNotificationParameters:
        return ImplicitDict.parse(
            self.v22a_query.request.json,
            v22a_api.PutIdentificationServiceAreaNotificationParameters,
        )

    @property
    def isa(self) -> ISA | None:
        if self.rid_version == RIDVersion.f3411_19:
            return ISA(
                v19_value=(
                    self._v19_request.service_area
                    if "service_area" in self._v19_request
                    else None
                )
            )
        elif self.rid_version == RIDVersion.f3411_22a:
            return ISA(
                v22a_value=(
                    self._v22a_request.service_area
                    if "service_area" in self._v22a_request
                    else None
                )
            )
        else:
            raise NotImplementedError(
                f"Cannot retrieve ISA using RID version {self.rid_version}"
            )

    @property
    def isa_id(self) -> str:
        if self.rid_version == RIDVersion.f3411_19:
            url = self.v19_query.request.url
        elif self.rid_version == RIDVersion.f3411_22a:
            url = self.v22a_query.request.url
        else:
            raise NotImplementedError(
                f"Cannot retrieve ISA ID using RID version {self.rid_version}"
            )
        return url.split("?")[0].split("/")[-1]


yaml.add_representer(ChangedSubscription, Representer.represent_dict)
yaml.add_representer(ChangedISA, Representer.represent_dict)
yaml.add_representer(ISAChange, Representer.represent_dict)
