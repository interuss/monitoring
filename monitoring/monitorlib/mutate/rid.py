import datetime
from typing import Dict, List, Optional, Union

from implicitdict import ImplicitDict
import s2sphere

from monitoring.monitorlib.fetch.rid import RIDQuery, Subscription, ISA
from monitoring.monitorlib.rid import RIDVersion
from uas_standards.astm.f3411 import v19, v22a
import uas_standards.astm.f3411.v19.api
import uas_standards.astm.f3411.v19.constants
import uas_standards.astm.f3411.v22a.api
import uas_standards.astm.f3411.v22a.constants
import yaml
from yaml.representer import Representer

from monitoring.monitorlib import fetch, infrastructure, rid_v1, rid_v2


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
    def success(self) -> bool:
        return not self.errors

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


def upsert_subscription(
    area: s2sphere.LatLngRect,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    uss_base_url: str,
    subscription_id: str,
    rid_version: RIDVersion,
    utm_client: infrastructure.UTMClientSession,
    subscription_version: Optional[str] = None,
) -> ChangedSubscription:
    mutation = "create" if subscription_version is None else "update"
    if rid_version == RIDVersion.f3411_19:
        body = {
            "extents": {
                "spatial_volume": {
                    "footprint": {"vertices": rid_v1.vertices_from_latlng_rect(area)},
                    "altitude_lo": 0,
                    "altitude_hi": 3048,
                },
                "time_start": start_time.strftime(rid_v1.DATE_FORMAT),
                "time_end": end_time.strftime(rid_v1.DATE_FORMAT),
            },
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
                utm_client, op.verb, url, json=body, scope=v19.constants.Scope.Read
            ),
        )
    elif rid_version == RIDVersion.f3411_22a:
        body = {
            "extents": {
                "volume": {
                    "outline_polygon": rid_v2.make_polygon_outline(area),
                    "altitude_lower": rid_v2.make_altitude(0),
                    "altitude_upper": rid_v2.make_altitude(3048),
                },
                "time_start": rid_v2.make_time(start_time),
                "time_end": rid_v2.make_time(end_time),
            },
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
) -> ChangedSubscription:
    if rid_version == RIDVersion.f3411_19:
        op = v19.api.OPERATIONS[v19.api.OperationID.DeleteSubscription]
        url = op.path.format(id=subscription_id, version=subscription_version)
        return ChangedSubscription(
            mutation="delete",
            v19_query=fetch.query_and_describe(
                utm_client, op.verb, url, scope=v19.constants.Scope.Read
            ),
        )
    elif rid_version == RIDVersion.f3411_22a:
        op = v22a.api.OPERATIONS[v22a.api.OperationID.DeleteSubscription]
        url = op.path.format(id=subscription_id, version=subscription_version)
        return ChangedSubscription(
            mutation="delete",
            v22a_query=fetch.query_and_describe(
                utm_client, op.verb, url, scope=v22a.constants.Scope.DisplayProvider
            ),
        )
    else:
        raise NotImplementedError(
            f"Cannot delete subscription using RID version {rid_version}"
        )


class ISAChangeNotification(RIDQuery):
    """Version-independent representation of response to a USS notification following an ISA change in the DSS."""

    @property
    def success(self) -> bool:
        # Tolerate not-strictly-correct 200 response
        return self.status_code == 204 or self.status_code == 200


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
    def success(self) -> bool:
        return not self.errors

    @property
    def errors(self) -> List[str]:
        if self.status_code != 200:
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
    def subscribers(self) -> List[SubscriberToNotify]:
        if self.rid_version == RIDVersion.f3411_19:
            return [
                SubscriberToNotify(v19_value=sub)
                for sub in self._v19_response.subscribers
            ]
        elif self.rid_version == RIDVersion.f3411_22a:
            return [
                SubscriberToNotify(v22a_value=sub)
                for sub in self._v22a_response.subscribers
            ]
        else:
            raise NotImplementedError(
                f"Cannot retrieve subscribers to notify using RID version {self.rid_version}"
            )


class ISAChange(ImplicitDict):
    """Result of an attempt to change an ISA (including DSS & notifications)"""

    dss_query: ChangedISA

    notifications: Dict[str, ISAChangeNotification]
    """Mapping from USS base URL to change notification query"""


def put_isa(
    area: s2sphere.LatLngRect,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    uss_base_url: str,
    isa_id: str,
    rid_version: RIDVersion,
    utm_client: infrastructure.UTMClientSession,
    isa_version: Optional[str] = None,
) -> ISAChange:
    mutation = "create" if isa_version is None else "update"
    if rid_version == RIDVersion.f3411_19:
        body = {
            "extents": {
                "spatial_volume": {
                    "footprint": {"vertices": rid_v1.vertices_from_latlng_rect(area)},
                    "altitude_lo": 0,
                    "altitude_hi": 3048,
                },
                "time_start": start_time.strftime(rid_v1.DATE_FORMAT),
                "time_end": end_time.strftime(rid_v1.DATE_FORMAT),
            },
            "flights_url": uss_base_url
            + v19.api.OPERATIONS[v19.api.OperationID.SearchFlights].path,
        }
        if isa_version is None:
            op = v19.api.OPERATIONS[v19.api.OperationID.CreateIdentificationServiceArea]
            url = op.path.format(id=isa_id)
        else:
            op = v19.api.OPERATIONS[v19.api.OperationID.UpdateIdentificationServiceArea]
            url = op.path.format(id=isa_id, version=isa_version)
        dss_response = ChangedISA(
            mutation=mutation,
            v19_query=fetch.query_and_describe(
                utm_client, op.verb, url, json=body, scope=v19.constants.Scope.Write
            ),
        )
    elif rid_version == RIDVersion.f3411_22a:
        body = {
            "extents": {
                "volume": {
                    "outline_polygon": rid_v2.make_polygon_outline(area),
                    "altitude_lower": rid_v2.make_altitude(0),
                    "altitude_upper": rid_v2.make_altitude(3048),
                },
                "time_start": rid_v2.make_time(start_time),
                "time_end": rid_v2.make_time(end_time),
            },
            "uss_base_url": uss_base_url,
        }
        if isa_version is None:
            op = v22a.api.OPERATIONS[v22a.api.OperationID.CreateSubscription]
            url = op.path.format(id=isa_id)
        else:
            op = v22a.api.OPERATIONS[v22a.api.OperationID.UpdateSubscription]
            url = op.path.format(id=isa_id, version=isa_version)
        dss_response = ChangedISA(
            mutation=mutation,
            v22a_query=fetch.query_and_describe(
                utm_client,
                op.verb,
                url,
                json=body,
                scope=v22a.constants.Scope.ServiceProvider,
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
) -> ISAChange:
    if rid_version == RIDVersion.f3411_19:
        op = v19.api.OPERATIONS[v19.api.OperationID.DeleteIdentificationServiceArea]
        url = op.path.format(id=isa_id, version=isa_version)
        dss_response = ChangedISA(
            mutation="delete",
            v19_query=fetch.query_and_describe(
                utm_client, op.verb, url, scope=v19.constants.Scope.Write
            ),
        )
    elif rid_version == RIDVersion.f3411_22a:
        op = v22a.api.OPERATIONS[v22a.api.OperationID.UpdateSubscription]
        url = op.path.format(id=isa_id, version=isa_version)
        dss_response = ChangedISA(
            mutation="delete",
            v22a_query=fetch.query_and_describe(
                utm_client, op.verb, url, scope=v22a.constants.Scope.ServiceProvider
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
