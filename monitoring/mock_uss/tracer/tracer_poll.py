import datetime
import json
import sys
from typing import Optional, Dict

from implicitdict import ImplicitDict

from monitoring.mock_uss.tracer.config import (
    KEY_TRACER_OUTPUT_FOLDER,
    KEY_TRACER_KML_SERVER,
    KEY_TRACER_KML_FOLDER,
)
from monitoring.mock_uss.tracer.observation_areas import (
    ObservationAreaID,
    ObservationArea,
)
from monitoring.monitorlib import versioning, fetch
from monitoring.mock_uss import webapp
from monitoring.mock_uss.tracer import diff, tracerlog
from monitoring.mock_uss.tracer.database import db
from monitoring.mock_uss.tracer import context
from monitoring.monitorlib.fetch.rid import FetchedISAs
from monitoring.monitorlib.fetch.scd import FetchedEntities
from monitoring.monitorlib.geo import make_latlng_rect, get_latlngrect_vertices
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.monitorlib.multiprocessing import SynchronizedValue


TASK_POLL_OBSERVATION_AREAS = "tracer poll observation areas"


class PollingStatus(ImplicitDict):
    started: bool = False


polling_status = SynchronizedValue(
    PollingStatus(),
    capacity_bytes=1000,
    decoder=lambda b: ImplicitDict.parse(json.loads(b.decode("utf-8")), PollingStatus),
)


class PollingValues(ImplicitDict):
    need_line_break: bool = False
    last_isa_result: Optional[FetchedISAs] = None
    last_ops_result: Optional[FetchedEntities] = None
    last_constraints_result: Optional[FetchedEntities] = None


polling_values = SynchronizedValue(
    PollingValues(),
    decoder=lambda b: ImplicitDict.parse(json.loads(b.decode("utf-8")), PollingValues),
)


def print_no_newline(s):
    sys.stdout.write(s)
    sys.stdout.flush()


def _log_poll_start(logger):
    init = False
    with polling_status as tx:
        if not tx.started:
            init = True
            tx.started = True
    if init:
        config = {
            KEY_TRACER_OUTPUT_FOLDER: webapp.config[KEY_TRACER_OUTPUT_FOLDER],
            KEY_TRACER_KML_SERVER: webapp.config[KEY_TRACER_KML_SERVER],
            KEY_TRACER_KML_FOLDER: webapp.config[KEY_TRACER_KML_FOLDER],
            "code_version": versioning.get_code_version(),
        }
        logger.log_new("poll_start", config)


@webapp.periodic_task(TASK_POLL_OBSERVATION_AREAS)
def poll_observation_areas() -> None:
    logger = context.tracer_logger
    _log_poll_start(logger)
    observation_areas: Dict[
        ObservationAreaID, ObservationArea
    ] = db.value.observation_areas
    for observation_area in observation_areas.values():
        if observation_area.f3411 is not None and observation_area.f3411.poll:
            poll_isas(observation_area, logger)
        if observation_area.f3548 is not None and observation_area.f3548.poll:
            scd_client = context.get_client(
                observation_area.f3548.auth_spec,
                observation_area.f3548.dss_base_url,
            )
            if observation_area.f3548.monitor_op_intents:
                poll_ops(observation_area, scd_client, logger)
            if observation_area.f3548.monitor_constraints:
                poll_constraints(observation_area, scd_client, logger)


def poll_isas(area: ObservationArea, logger: tracerlog.Logger) -> None:
    rid_client = context.get_client(area.f3411.auth_spec, area.f3411.dss_base_url)
    box = get_latlngrect_vertices(make_latlng_rect(area.area.volume))

    log_name = "poll_isas"
    t0 = datetime.datetime.utcnow()
    result = fetch.rid.isas(
        box,
        area.area.time_start.datetime,
        area.area.time_end.datetime,
        area.f3411.rid_version,
        rid_client,
    )
    t1 = datetime.datetime.utcnow()

    log_new = False
    last_result = None
    with polling_values as tx:
        assert isinstance(tx, PollingValues)
        if tx.last_isa_result is None or result.has_different_content_than(
            tx.last_isa_result
        ):
            last_result = tx.last_isa_result
            log_new = True
            tx.need_line_break = False
            tx.last_isa_result = result
        else:
            tx.need_line_break = True
        need_line_break = tx.need_line_break

    if log_new:
        logger.log_new(log_name, result)
        if need_line_break:
            print()
        print(diff.isa_diff_text(last_result, result))
    else:
        logger.log_same(t0, t1, log_name)
        print_no_newline(".")


def poll_ops(
    area: ObservationArea, scd_client: UTMClientSession, logger: tracerlog.Logger
) -> None:
    box = make_latlng_rect(area.area.volume)
    log_name = "poll_ops"
    t0 = datetime.datetime.utcnow()
    if "operational_intents" not in context.scd_cache:
        context.scd_cache["operational_intents"]: Dict[
            str, fetch.scd.FetchedEntity
        ] = {}
    result = fetch.scd.operations(
        scd_client,
        box,
        area.area.time_start.datetime,
        area.area.time_end.datetime,
        operation_cache=context.scd_cache["operational_intents"],
    )
    t1 = datetime.datetime.utcnow()

    log_new = False
    last_result = None
    with polling_values as tx:
        if tx.last_ops_result is None or result.has_different_content_than(
            tx.last_ops_result
        ):
            last_result = tx.last_ops_result
            log_new = True
            tx.need_line_break = False
            tx.last_ops_result = result
        else:
            tx.need_line_break = True
        need_line_break = tx.need_line_break

    if log_new:
        logger.log_new(log_name, result)
        if need_line_break:
            print()
        print(diff.entity_diff_text(last_result, result))
    else:
        logger.log_same(t0, t1, log_name)
        print_no_newline(".")


def poll_constraints(
    area: ObservationArea, scd_client: UTMClientSession, logger: tracerlog.Logger
) -> None:
    box = make_latlng_rect(area.area.volume)
    log_name = "poll_constraints"
    t0 = datetime.datetime.utcnow()
    if "constraints" not in context.scd_cache:
        context.scd_cache["constraints"]: Dict[str, fetch.scd.FetchedEntity] = {}
    result = fetch.scd.constraints(
        scd_client,
        box,
        area.area.time_start.datetime,
        area.area.time_end.datetime,
        constraint_cache=context.scd_cache["constraints"],
    )
    t1 = datetime.datetime.utcnow()

    log_new = False
    last_result = None
    with polling_values as tx:
        if result.has_different_content_than(tx.last_constraints_result):
            last_result = tx.last_constraints_result
            log_new = True
            tx.need_line_break = False
            tx.last_constraints_result = result
        else:
            tx.need_line_break = True
        need_line_break = tx.need_line_break

    if log_new:
        logger.log_new(log_name, result)
        if need_line_break:
            print()
        print(diff.entity_diff_text(last_result, result))
    else:
        logger.log_same(t0, t1, log_name)
        print_no_newline(".")
