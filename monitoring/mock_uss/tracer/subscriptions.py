import uuid

import arrow
import yaml
from implicitdict import StringBasedDateTime
from yaml.representer import Representer

import monitoring.monitorlib.fetch.rid as fetch_rid
import monitoring.monitorlib.fetch.scd as fetch_scd
import monitoring.monitorlib.mutate.rid as mutate_rid
import monitoring.monitorlib.mutate.scd as mutate_scd
from monitoring.mock_uss.app import config, webapp
from monitoring.mock_uss.tracer import context
from monitoring.mock_uss.tracer.log_types import (
    RIDSubscribe,
    RIDUnsubscribe,
    SCDSubscribe,
    SCDUnsubscribe,
)
from monitoring.mock_uss.tracer.observation_areas import ObservationAreaID
from monitoring.monitorlib.geo import get_latlngrect_vertices, make_latlng_rect
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.monitorlib.rid import RIDVersion

yaml.add_representer(StringBasedDateTime, Representer.represent_str)


class SubscriptionManagementError(RuntimeError):
    def __init__(self, msg):
        super().__init__(msg)


def subscribe_rid(
    area_id: ObservationAreaID,
    area: Volume4D,
    rid_version: RIDVersion,
    rid_client: UTMClientSession,
) -> str:
    logger = context.tracer_logger
    subscription_id = str(uuid.uuid4())
    vertices = get_latlngrect_vertices(make_latlng_rect(area.volume))
    base_url = webapp.config[config.KEY_BASE_URL]
    if rid_version == RIDVersion.f3411_19:
        uss_base_url = f"{base_url}/tracer/f3411v19/{area_id}"
    elif rid_version == RIDVersion.f3411_22a:
        uss_base_url = f"{base_url}/tracer/f3411v22a/{area_id}/v2"
    else:
        raise NotImplementedError(
            f"Cannot subscribe to ISA updates using RID version {rid_version}"
        )

    create_result = mutate_rid.upsert_subscription(
        area_vertices=vertices,
        alt_lo=area.volume.altitude_lower_wgs84_m(0),
        alt_hi=area.volume.altitude_upper_wgs84_m(3048),
        start_time=area.time_start.datetime if area.time_start else None,
        end_time=area.time_end.datetime if area.time_end else None,
        uss_base_url=uss_base_url,
        subscription_id=subscription_id,
        rid_version=rid_version,
        utm_client=rid_client,
    )
    logger.log_new(
        RIDSubscribe(
            changed_subscription=create_result,
            recorded_at=StringBasedDateTime(arrow.utcnow()),
        )
    )
    if not create_result.success:
        raise SubscriptionManagementError("Could not create RID Subscription")
    return subscription_id


def subscribe_scd(
    area_id: ObservationAreaID,
    area: Volume4D,
    op_intents: bool,
    constraints: bool,
    scd_client: UTMClientSession,
) -> str:
    logger = context.tracer_logger
    subscription_id = str(uuid.uuid4())
    box = make_latlng_rect(area.volume)
    base_url = webapp.config[config.KEY_BASE_URL]
    uss_base_url = f"{base_url}/tracer/f3548v21/{area_id}"

    if not area.time_start or not area.time_end:
        raise SubscriptionManagementError(
            "Could not create new SCD Subscription -> time_start or time_end not set"
        )

    create_result = mutate_scd.upsert_subscription(
        scd_client,
        box,
        area.time_start.datetime,
        area.time_end.datetime,
        uss_base_url,
        subscription_id,
        op_intents,
        constraints,
        area.volume.altitude_lower_wgs84_m(0),
        area.volume.altitude_upper_wgs84_m(3048),
    )
    logfile = logger.log_new(
        SCDSubscribe(
            changed_subscription=create_result,
            recorded_at=StringBasedDateTime(arrow.utcnow()),
        )
    )
    if not create_result.success:
        raise SubscriptionManagementError(
            f"Could not create new SCD Subscription -> {logfile}"
        )
    return subscription_id


def unsubscribe_rid(
    subscription_id: str, rid_version: RIDVersion, rid_client: UTMClientSession
) -> None:
    logger = context.tracer_logger
    existing_result = fetch_rid.subscription(subscription_id, rid_version, rid_client)
    if existing_result.status_code != 404 and not existing_result.success:
        logfile = logger.log_new(
            RIDUnsubscribe(
                existing_subscription=existing_result,
                recorded_at=StringBasedDateTime(arrow.utcnow()),
            )
        )
        raise SubscriptionManagementError(
            f"Could not query existing RID Subscription -> {logfile}"
        )

    if existing_result.subscription is not None:
        del_result = mutate_rid.delete_subscription(
            subscription_id=subscription_id,
            subscription_version=existing_result.subscription.version,
            rid_version=rid_version,
            utm_client=rid_client,
        )
        logfile = logger.log_new(
            RIDUnsubscribe(
                existing_subscription=existing_result,
                deleted_subscription=del_result,
                recorded_at=StringBasedDateTime(arrow.utcnow()),
            )
        )
        if not del_result.success:
            raise SubscriptionManagementError(
                f"Could not delete existing RID Subscription -> {logfile}"
            )


def unsubscribe_scd(subscription_id: str, scd_client: UTMClientSession) -> None:
    logger = context.tracer_logger
    get_result = fetch_scd.get_subscription(scd_client, subscription_id)
    if not (get_result.success or get_result.was_not_found):
        logfile = logger.log_new(
            SCDUnsubscribe(
                existing_subscription=get_result,
                recorded_at=StringBasedDateTime(arrow.utcnow()),
            )
        )
        raise SubscriptionManagementError(
            f"Could not query existing SCD Subscription -> {logfile}"
        )

    if get_result.subscription is not None:
        del_result = mutate_scd.delete_subscription(
            scd_client,
            subscription_id,
            get_result.subscription.version,
        )
        logfile = logger.log_new(
            SCDUnsubscribe(
                existing_subscription=get_result,
                deleted_subscription=del_result,
                recorded_at=StringBasedDateTime(arrow.utcnow()),
            )
        )
        if not del_result.success:
            raise SubscriptionManagementError(
                f"Could not delete existing SCD Subscription -> {logfile}"
            )
