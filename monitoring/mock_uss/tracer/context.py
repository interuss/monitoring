import datetime
import os
import sys
from typing import Optional

from implicitdict import StringBasedDateTime
from loguru import logger
import yaml
from yaml.representer import Representer

from monitoring.mock_uss.tracer.tracer_poll import (
    TASK_POLL_ISAS,
    TASK_POLL_OPS,
    TASK_POLL_CONSTRAINTS,
)
from monitoring.mock_uss.tracer.config import KEY_RID_VERSION
from monitoring.monitorlib import ids, versioning
from monitoring.monitorlib import fetch
import monitoring.monitorlib.fetch.rid
import monitoring.monitorlib.fetch.scd
from monitoring.monitorlib import mutate
import monitoring.monitorlib.mutate.rid
import monitoring.monitorlib.mutate.scd
from monitoring.mock_uss import config, webapp, SERVICE_TRACER
from monitoring.mock_uss.tracer.resources import ResourceSet, get_options
from monitoring.mock_uss.tracer.database import db
from monitoring.monitorlib.rid import RIDVersion

yaml.add_representer(StringBasedDateTime, Representer.represent_str)

RID_SUBSCRIPTION_ID_CODE = "tracer RID Subscription"
SCD_SUBSCRIPTION_ID_CODE = "tracer SCD Subscription"

RID_VERSION = webapp.config[KEY_RID_VERSION]

resources: Optional[ResourceSet] = None


class SubscriptionManagementError(RuntimeError):
    def __init__(self, msg):
        super(SubscriptionManagementError, self).__init__(msg)


@webapp.setup_task("tracer context creation")
def init() -> None:
    args = get_options()

    # Enable polling tasks
    if args.rid_isa_poll_interval:
        webapp.set_task_period(
            TASK_POLL_ISAS, datetime.timedelta(seconds=args.rid_isa_poll_interval)
        )
    if args.scd_operation_poll_interval:
        webapp.set_task_period(
            TASK_POLL_OPS, datetime.timedelta(seconds=args.scd_operation_poll_interval)
        )
    if args.scd_constraint_poll_interval:
        webapp.set_task_period(
            TASK_POLL_CONSTRAINTS,
            datetime.timedelta(seconds=args.scd_constraint_poll_interval),
        )

    global resources
    resources = ResourceSet.from_arguments(args)

    cfg = vars(args)
    cfg["code_version"] = versioning.get_code_version()
    resources.logger.log_new("subscribe_start", cfg)

    base_url = webapp.config[config.KEY_BASE_URL]
    if base_url and (args.monitor_rid or args.monitor_scd):
        # Establish subscriptions
        try:
            logger.info(
                "Establishing Subscriptions from PID {} at {}...".format(
                    os.getpid(), datetime.datetime.utcnow()
                )
            )
            _subscribe(resources, base_url, args.monitor_rid, args.monitor_scd)
            logger.info("Subscriptions established.")
        except SubscriptionManagementError as e:
            msg = "Failed to initialize: {}".format(e)
            logger.error(msg)
            sys.stderr.write(msg)
            sys.exit(-1)


@webapp.shutdown_task("tracer cleanup")
def _shutdown():
    args = get_options()
    logger.info(
        "Cleaning up Subscriptions from PID {} at {}...".format(
            os.getpid(), datetime.datetime.utcnow()
        )
    )
    _unsubscribe(resources, args.monitor_rid, args.monitor_scd)
    logger.info("Subscription cleanup complete.")
    resources.logger.log_new(
        "subscribe_stop",
        {
            "timestamp": datetime.datetime.utcnow(),
        },
    )


def _subscribe(
    resources: ResourceSet, base_url: str, monitor_rid: bool, monitor_scd: bool
) -> None:
    if base_url.endswith("/"):
        base_url = base_url[0:-1]
    if monitor_rid:
        if RID_VERSION == RIDVersion.f3411_19:
            _subscribe_rid(resources, base_url + "/tracer/f3411v19")
        elif RID_VERSION == RIDVersion.f3411_22a:
            _subscribe_rid(resources, base_url + "/tracer/f3411v22a/v2")
        else:
            raise NotImplementedError(
                f"Cannot subscribe to DSS using RID version {RID_VERSION}"
            )

    if monitor_scd:
        _subscribe_scd(resources, base_url + "/tracer/f3548v21")


def _unsubscribe(resources: ResourceSet, monitor_rid: bool, monitor_scd: bool) -> None:
    if monitor_rid:
        _clear_existing_rid_subscription(resources, "cleanup")
    if monitor_scd:
        _clear_existing_scd_subscription(resources, "cleanup")


def _rid_subscription_id() -> str:
    sub_id = ids.make_id(RID_SUBSCRIPTION_ID_CODE)
    return str(sub_id)


RID_SUBSCRIPTION_KEY = "subscribe_ridsubscription"


def _subscribe_rid(resources: ResourceSet, uss_base_url: str) -> None:
    _clear_existing_rid_subscription(resources, "old")

    create_result = mutate.rid.upsert_subscription(
        area=resources.area,
        start_time=resources.start_time,
        end_time=resources.end_time,
        uss_base_url=uss_base_url,
        subscription_id=_rid_subscription_id(),
        rid_version=RID_VERSION,
        utm_client=resources.dss_clients["rid"],
    )
    resources.logger.log_new(RID_SUBSCRIPTION_KEY, create_result)
    if not create_result.success:
        raise SubscriptionManagementError("Could not create RID Subscription")


def _clear_existing_rid_subscription(resources: ResourceSet, suffix: str) -> None:
    existing_result = fetch.rid.subscription(
        _rid_subscription_id(), RID_VERSION, resources.dss_clients["rid"]
    )
    logfile = resources.logger.log_new(
        "{}_{}_get".format(RID_SUBSCRIPTION_KEY, suffix), existing_result
    )
    if existing_result.status_code != 404 and not existing_result.success:
        raise SubscriptionManagementError(
            "Could not query existing RID Subscription -> {}".format(logfile)
        )

    if existing_result.subscription is not None:
        del_result = mutate.rid.delete_subscription(
            subscription_id=_rid_subscription_id(),
            subscription_version=existing_result.subscription.version,
            rid_version=RID_VERSION,
            utm_client=resources.dss_clients["rid"],
        )
        logfile = resources.logger.log_new(
            "{}_{}_del".format(RID_SUBSCRIPTION_KEY, suffix), del_result
        )
        if not del_result.success:
            raise SubscriptionManagementError(
                "Could not delete existing RID Subscription -> {}".format(logfile)
            )


SCD_SUBSCRIPTION_KEY = "subscribe_scdsubscription"


def _scd_subscription_id() -> str:
    sub_id = ids.make_id(SCD_SUBSCRIPTION_ID_CODE)
    return str(sub_id)


def _subscribe_scd(resources: ResourceSet, base_url: str) -> None:
    _clear_existing_scd_subscription(resources, "old")

    create_result = mutate.scd.put_subscription(
        resources.dss_clients["scd"],
        resources.area,
        resources.start_time,
        resources.end_time,
        base_url,
        _scd_subscription_id(),
    )
    logfile = resources.logger.log_new(SCD_SUBSCRIPTION_KEY, create_result)
    if not create_result.success:
        raise SubscriptionManagementError(
            "Could not create new SCD Subscription -> {}".format(logfile)
        )


def _clear_existing_scd_subscription(resources: ResourceSet, suffix: str) -> None:
    get_result = fetch.scd.subscription(
        resources.dss_clients["scd"], _scd_subscription_id()
    )
    logfile = resources.logger.log_new(
        "{}_{}_get".format(SCD_SUBSCRIPTION_KEY, suffix), get_result
    )
    if not get_result.success:
        raise SubscriptionManagementError(
            "Could not query existing SCD Subscription -> {}".format(logfile)
        )

    if get_result.subscription is not None:
        del_result = mutate.scd.delete_subscription(
            resources.dss_clients["scd"],
            _scd_subscription_id(),
            get_result.subscription.version,
        )
        logfile = resources.logger.log_new(
            "{}_{}".format(SCD_SUBSCRIPTION_KEY, suffix), del_result
        )
        if not del_result.success:
            raise SubscriptionManagementError(
                "Could not delete existing SCD Subscription -> {}".format(logfile)
            )
