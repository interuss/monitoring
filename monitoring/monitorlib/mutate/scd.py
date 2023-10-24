import datetime
from typing import List, Optional

import s2sphere
import yaml
from yaml.representer import Representer

from monitoring.monitorlib import infrastructure, scd
from monitoring.monitorlib import fetch
from monitoring.monitorlib.geo import Polygon
from monitoring.monitorlib.geotemporal import Volume4D


class MutatedSubscription(fetch.Query):
    mutation: Optional[str] = None

    @property
    def success(self) -> bool:
        return not self.errors

    @property
    def errors(self) -> List[str]:
        if self.status_code != 200:
            return [
                "Failed to {} SCD Subscription ({})".format(
                    self.mutation, self.status_code
                )
            ]
        if self.json_result is None:
            return ["Response did not contain valid JSON"]
        sub = self.subscription
        if sub is None or not sub.valid:
            return ["Response returned an invalid Subscription"]

    @property
    def subscription(self) -> Optional[scd.Subscription]:
        if self.json_result is None:
            return None
        sub = self.json_result.get("subscription", None)
        if not sub:
            return None
        return scd.Subscription(sub)


yaml.add_representer(MutatedSubscription, Representer.represent_dict)


def put_subscription(
    utm_client: infrastructure.UTMClientSession,
    area: s2sphere.LatLngRect,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    base_url: str,
    subscription_id: str,
    notify_for_op_intents: bool,
    notify_for_constraints: bool,
    min_alt_m: float = 0,
    max_alt_m: float = 3048,
    version: Optional[str] = None,
    participant_id: Optional[str] = None,
) -> MutatedSubscription:
    body = {
        "extents": Volume4D.from_values(
            start_time,
            end_time,
            min_alt_m,
            max_alt_m,
            polygon=Polygon.from_latlng_rect(latlngrect=area),
        ).to_f3548v21(),
        "uss_base_url": base_url,
        "notify_for_operational_intents": notify_for_op_intents,
        "notify_for_constraints": notify_for_constraints,
    }
    url = "/dss/v1/subscriptions/{}".format(subscription_id)
    if version:
        url += f"/{version}"
    result = MutatedSubscription(
        fetch.query_and_describe(
            utm_client,
            "PUT",
            url,
            json=body,
            scope=scd.SCOPE_SC,
            participant_id=participant_id,
        )
    )
    result.mutation = "update" if version else "create"
    return result


def delete_subscription(
    utm_client: infrastructure.UTMClientSession,
    subscription_id: str,
    version: str,
    participant_id: Optional[str] = None,
) -> MutatedSubscription:
    url = f"/dss/v1/subscriptions/{subscription_id}/{version}"
    result = MutatedSubscription(
        fetch.query_and_describe(
            utm_client, "DELETE", url, scope=scd.SCOPE_SC, participant_id=participant_id
        )
    )
    result.mutation = "delete"
    return result
