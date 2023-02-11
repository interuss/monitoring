import atexit
import datetime
import os
import signal
import sys
from multiprocessing import Process
from typing import Optional

from implicitdict import StringBasedDateTime
from loguru import logger
import yaml
from yaml.representer import Representer

from monitoring.monitorlib import ids, versioning
from monitoring.monitorlib import fetch
import monitoring.monitorlib.fetch.rid
import monitoring.monitorlib.fetch.scd
from monitoring.monitorlib import mutate
import monitoring.monitorlib.mutate.rid
import monitoring.monitorlib.mutate.scd
from monitoring.mock_uss import config, webapp
from monitoring.mock_uss.tracer import tracer_poll
from monitoring.mock_uss.tracer.resources import ResourceSet, get_options
from monitoring.mock_uss.tracer.database import db
from monitoring.monitorlib.rid_common import RIDVersion

yaml.add_representer(StringBasedDateTime, Representer.represent_str)

RID_SUBSCRIPTION_ID_CODE = "tracer RID Subscription"
SCD_SUBSCRIPTION_ID_CODE = "tracer SCD Subscription"

resources: Optional[ResourceSet] = None


class SubscriptionManagementError(RuntimeError):
    def __init__(self, msg):
        super(SubscriptionManagementError, self).__init__(msg)


def init() -> None:
    perform_setup = False
    with db as tx:
        if not tx.setup_initiated:
            tx.setup_initiated = True
            perform_setup = True
    if not perform_setup:
        logger.info(f"Skipping setup on process ID {os.getpid()}")
        return
    logger.info(f"Initiating setup on process ID {os.getpid()}")

    args = get_options()

    # Initiate polling loop
    if (
        args.rid_isa_poll_interval
        or args.scd_operation_poll_interval
        or args.scd_constraint_poll_interval
    ):
        logger.info("Initiating polling loop")
        p = Process(target=tracer_poll.poll_loop)
        p.start()
        logger.info(f"Polling loop on process ID {p.pid}, initiated by {os.getpid()}")

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

    shutdown = lambda signal_number: _shutdown(p, signal_number)
    atexit.register(shutdown, None)
    for sig in (signal.SIGABRT, signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, shutdown)


def initiate_shutdown():
    with db as tx:
        tx.stopping = True
    os.kill(os.getpid(), signal.SIGINT)


def _shutdown(p: Process, signal_number):
    should_cleanup = False
    with db as tx:
        if tx.stopping and not tx.cleanup_initiated:
            tx.cleanup_initiated = True
            should_cleanup = True
    if not should_cleanup:
        logger.info(f"Not cleaning up Subscriptions from process {os.getpid()}")
        return

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
            "signal_number": signal_number,
        },
    )


def _subscribe(
    resources: ResourceSet, base_url: str, monitor_rid: bool, monitor_scd: bool
) -> None:
    if base_url.endswith("/"):
        base_url = base_url[0:-1]
    if monitor_rid:
        _subscribe_rid(
            resources, base_url + "/tracer/f3411v19/v1/uss/identification_service_areas"
        )
    if monitor_scd:
        _subscribe_scd(resources, base_url)


def _unsubscribe(resources: ResourceSet, monitor_rid: bool, monitor_scd: bool) -> None:
    if monitor_rid:
        _clear_existing_rid_subscription(resources, "cleanup")
    if monitor_scd:
        _clear_existing_scd_subscription(resources, "cleanup")


def _rid_subscription_id() -> str:
    sub_id = ids.make_id(RID_SUBSCRIPTION_ID_CODE)
    return str(sub_id)


RID_SUBSCRIPTION_KEY = "subscribe_ridsubscription"


def _subscribe_rid(resources: ResourceSet, callback_url: str) -> None:
    _clear_existing_rid_subscription(resources, "old")

    create_result = mutate.rid.put_subscription(
        resources.dss_client,
        resources.area,
        resources.start_time,
        resources.end_time,
        callback_url,
        _rid_subscription_id(),
    )
    resources.logger.log_new(RID_SUBSCRIPTION_KEY, create_result)
    if not create_result.success:
        raise SubscriptionManagementError("Could not create RID Subscription")


def _clear_existing_rid_subscription(resources: ResourceSet, suffix: str) -> None:
    existing_result = fetch.rid.subscription(
        _rid_subscription_id(), RIDVersion.f3411_19, resources.dss_client
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
            resources.dss_client,
            _rid_subscription_id(),
            existing_result.subscription.version,
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
        resources.dss_client,
        resources.area,
        resources.start_time,
        resources.end_time,
        base_url + "/tracer/f3548v21",
        _scd_subscription_id(),
    )
    logfile = resources.logger.log_new(SCD_SUBSCRIPTION_KEY, create_result)
    if not create_result.success:
        raise SubscriptionManagementError(
            "Could not create new SCD Subscription -> {}".format(logfile)
        )


def _clear_existing_scd_subscription(resources: ResourceSet, suffix: str) -> None:
    get_result = fetch.scd.subscription(resources.dss_client, _scd_subscription_id())
    logfile = resources.logger.log_new(
        "{}_{}_get".format(SCD_SUBSCRIPTION_KEY, suffix), get_result
    )
    if not get_result.success:
        raise SubscriptionManagementError(
            "Could not query existing SCD Subscription -> {}".format(logfile)
        )

    if get_result.subscription is not None:
        del_result = mutate.scd.delete_subscription(
            resources.dss_client,
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
