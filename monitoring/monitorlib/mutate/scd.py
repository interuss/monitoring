import datetime
from typing import List, Optional

import s2sphere
import yaml
from implicitdict import ImplicitDict
from uas_standards.astm.f3548.v21.api import OPERATIONS, OperationID, Subscription
from yaml.representer import Representer

from monitoring.monitorlib import fetch
from monitoring.monitorlib import infrastructure, scd
from monitoring.monitorlib.fetch import QueryType
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

    @property
    def subscription(self) -> Optional[Subscription]:
        if self.json_result is None:
            return None
        try:
            # We get a ValueError if .parse is fed a None,
            # or if the JSON can't be parsed as a Subscription.
            return ImplicitDict.parse(
                self.json_result.get("subscription", None),
                Subscription,
            )
        except ValueError:
            return None


yaml.add_representer(MutatedSubscription, Representer.represent_dict)


def upsert_subscription(
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
    is_creation = version is None
    if is_creation:
        op = OPERATIONS[OperationID.CreateSubscription]
        path = op.path.format(subscriptionid=subscription_id)
        query_type = QueryType.F3548v21DSSCreateSubscription
    else:
        op = OPERATIONS[OperationID.UpdateSubscription]
        path = op.path.format(subscriptionid=subscription_id, version=version)
        query_type = QueryType.F3548v21DSSUpdateSubscription

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

    result = MutatedSubscription(
        fetch.query_and_describe(
            utm_client,
            op.verb,
            path,
            json=body,
            scope=scd.SCOPE_SC,
            query_type=query_type,
            participant_id=participant_id,
        )
    )
    result.mutation = "create" if is_creation else "update"
    return result


def delete_subscription(
    utm_client: infrastructure.UTMClientSession,
    subscription_id: str,
    version: str,
    participant_id: Optional[str] = None,
) -> MutatedSubscription:
    op = OPERATIONS[OperationID.DeleteSubscription]
    result = MutatedSubscription(
        fetch.query_and_describe(
            utm_client,
            op.verb,
            op.path.format(subscriptionid=subscription_id, version=version),
            QueryType.F3548v21DSSDeleteSubscription,
            scope=scd.SCOPE_SC,
            participant_id=participant_id,
        )
    )
    result.mutation = "delete"
    return result
