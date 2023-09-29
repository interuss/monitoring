import uuid

from implicitdict import StringBasedDateTime
import yaml
from yaml.representer import Representer

from monitoring.mock_uss.tracer import context
from monitoring.mock_uss.tracer.observation_areas import ObservationAreaID
from monitoring.monitorlib import fetch
import monitoring.monitorlib.fetch.rid
import monitoring.monitorlib.fetch.scd
from monitoring.monitorlib import mutate
import monitoring.monitorlib.mutate.rid
import monitoring.monitorlib.mutate.scd
from monitoring.mock_uss import config, webapp
from monitoring.monitorlib.geo import make_latlng_rect, get_latlngrect_vertices
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.monitorlib.rid import RIDVersion

yaml.add_representer(StringBasedDateTime, Representer.represent_str)

RID_SUBSCRIPTION_ID_CODE = "tracer RID Subscription"
SCD_SUBSCRIPTION_ID_CODE = "tracer SCD Subscription"
RID_SUBSCRIPTION_KEY = "subscription_rid"
SCD_SUBSCRIPTION_KEY = "subscription_scd"


class SubscriptionManagementError(RuntimeError):
    def __init__(self, msg):
        super(SubscriptionManagementError, self).__init__(msg)


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

    create_result = mutate.rid.upsert_subscription(
        area_vertices=vertices,
        alt_lo=area.volume.altitude_lower_wgs84_m(0),
        alt_hi=area.volume.altitude_upper_wgs84_m(3048),
        start_time=area.time_start.datetime,
        end_time=area.time_end.datetime,
        uss_base_url=uss_base_url,
        subscription_id=subscription_id,
        rid_version=rid_version,
        utm_client=rid_client,
    )
    logger.log_new(f"{RID_SUBSCRIPTION_KEY}_create", create_result)
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

    create_result = mutate.scd.put_subscription(
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
    logfile = logger.log_new(f"{SCD_SUBSCRIPTION_KEY}_create", create_result)
    if not create_result.success:
        raise SubscriptionManagementError(
            "Could not create new SCD Subscription -> {}".format(logfile)
        )
    return subscription_id


def unsubscribe_rid(
    subscription_id: str, rid_version: RIDVersion, rid_client: UTMClientSession
) -> None:
    logger = context.tracer_logger
    existing_result = fetch.rid.subscription(subscription_id, rid_version, rid_client)
    logfile = logger.log_new(f"{RID_SUBSCRIPTION_KEY}_get", existing_result)
    if existing_result.status_code != 404 and not existing_result.success:
        raise SubscriptionManagementError(
            "Could not query existing RID Subscription -> {}".format(logfile)
        )

    if existing_result.subscription is not None:
        del_result = mutate.rid.delete_subscription(
            subscription_id=subscription_id,
            subscription_version=existing_result.subscription.version,
            rid_version=rid_version,
            utm_client=rid_client,
        )
        logfile = logger.log_new(f"{RID_SUBSCRIPTION_KEY}_del", del_result)
        if not del_result.success:
            raise SubscriptionManagementError(
                "Could not delete existing RID Subscription -> {}".format(logfile)
            )


def unsubscribe_scd(subscription_id: str, scd_client: UTMClientSession) -> None:
    logger = context.tracer_logger
    get_result = fetch.scd.subscription(scd_client, subscription_id)
    logfile = logger.log_new(f"{SCD_SUBSCRIPTION_KEY}_get", get_result)
    if not get_result.success:
        raise SubscriptionManagementError(
            "Could not query existing SCD Subscription -> {}".format(logfile)
        )

    if get_result.subscription is not None:
        del_result = mutate.scd.delete_subscription(
            scd_client,
            subscription_id,
            get_result.subscription.version,
        )
        logfile = logger.log_new(f"{SCD_SUBSCRIPTION_KEY}_del", del_result)
        if not del_result.success:
            raise SubscriptionManagementError(
                "Could not delete existing SCD Subscription -> {}".format(logfile)
            )
