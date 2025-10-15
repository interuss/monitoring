import datetime
import json
import sys

import arrow
from implicitdict import ImplicitDict, StringBasedDateTime

from monitoring.mock_uss.app import webapp
from monitoring.mock_uss.tracer import context, diff, tracerlog
from monitoring.mock_uss.tracer.config import (
    KEY_TRACER_KML_FOLDER,
    KEY_TRACER_KML_SERVER,
    KEY_TRACER_OUTPUT_FOLDER,
)
from monitoring.mock_uss.tracer.database import db
from monitoring.mock_uss.tracer.log_types import (
    PollConstraints,
    PollISAs,
    PollOperationalIntents,
    PollStart,
)
from monitoring.mock_uss.tracer.observation_areas import (
    ObservationArea,
    ObservationAreaID,
)
from monitoring.monitorlib import versioning
from monitoring.monitorlib.fetch.rid import FetchedISAs
from monitoring.monitorlib.fetch.rid import isas as fetch_rid_isas
from monitoring.monitorlib.fetch.scd import (
    FetchedEntities,
)
from monitoring.monitorlib.fetch.scd import (
    constraints as fetch_scd_constraints,
)
from monitoring.monitorlib.fetch.scd import (
    operations as fetch_scd_operations,
)
from monitoring.monitorlib.geo import get_latlngrect_vertices, make_latlng_rect
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.monitorlib.multiprocessing import SynchronizedValue

TASK_POLL_OBSERVATION_AREAS = "tracer poll observation areas"


class PollingStatus(ImplicitDict):
    started: bool = False


polling_status = SynchronizedValue[PollingStatus](
    PollingStatus(),
    capacity_bytes=1000,
    decoder=lambda b: ImplicitDict.parse(json.loads(b.decode("utf-8")), PollingStatus),
)


class PollingValues(ImplicitDict):
    need_line_break: bool = False
    last_isa_result: FetchedISAs | None = None
    last_ops_result: FetchedEntities | None = None
    last_constraints_result: FetchedEntities | None = None


polling_values = SynchronizedValue[PollingValues](
    PollingValues(),
    decoder=lambda b: ImplicitDict.parse(json.loads(b.decode("utf-8")), PollingValues),
)


def print_no_newline(s):
    sys.stdout.write(s)
    sys.stdout.flush()


def _log_poll_start(logger):
    init = False
    with polling_status.transact() as tx:
        if not tx.value.started:
            init = True
            tx.value.started = True
    if init:
        config = {
            KEY_TRACER_OUTPUT_FOLDER: webapp.config[KEY_TRACER_OUTPUT_FOLDER],
            KEY_TRACER_KML_SERVER: webapp.config[KEY_TRACER_KML_SERVER],
            KEY_TRACER_KML_FOLDER: webapp.config[KEY_TRACER_KML_FOLDER],
            "code_version": versioning.get_code_version(),
        }
        logger.log_new(
            PollStart(config=config, recorded_at=StringBasedDateTime(arrow.utcnow()))
        )


@webapp.periodic_task(TASK_POLL_OBSERVATION_AREAS)
def poll_observation_areas() -> None:
    logger = context.tracer_logger
    _log_poll_start(logger)
    observation_areas: dict[ObservationAreaID, ObservationArea] = (
        db.value.observation_areas
    )
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
    if not area.f3411:
        return

    rid_client = context.get_client(area.f3411.auth_spec, area.f3411.dss_base_url)
    box = get_latlngrect_vertices(make_latlng_rect(area.area.volume))

    t0 = datetime.datetime.now(datetime.UTC)
    result = fetch_rid_isas(
        box,
        area.area.time_start.datetime if area.area.time_start else None,
        area.area.time_end.datetime if area.area.time_end else None,
        area.f3411.rid_version,
        rid_client,
    )
    t1 = datetime.datetime.now(datetime.UTC)

    log_new = False
    last_result = None
    with polling_values.transact() as tx:
        if tx.value.last_isa_result is None or result.has_different_content_than(
            tx.value.last_isa_result
        ):
            last_result = tx.value.last_isa_result
            log_new = True
            tx.value.need_line_break = False
            tx.value.last_isa_result = result
        else:
            tx.value.need_line_break = True
        need_line_break = tx.value.need_line_break

    log_entry = PollISAs(poll=result, recorded_at=StringBasedDateTime(arrow.utcnow()))
    if log_new:
        logger.log_new(log_entry)
        if need_line_break:
            print()
        print(diff.isa_diff_text(last_result, result))
    else:
        logger.log_same(t0, t1, log_entry.prefix_code())
        print_no_newline(".")


def poll_ops(
    area: ObservationArea, scd_client: UTMClientSession, logger: tracerlog.Logger
) -> None:
    if not area.area.time_start or not area.area.time_end:
        return

    box = make_latlng_rect(area.area.volume)
    t0 = datetime.datetime.now(datetime.UTC)
    if "operational_intents" not in context.scd_cache:
        context.scd_cache["operational_intents"] = {}
    result = fetch_scd_operations(
        scd_client,
        box,
        area.area.time_start.datetime,
        area.area.time_end.datetime,
        operation_cache=context.scd_cache["operational_intents"],
    )
    t1 = datetime.datetime.now(datetime.UTC)

    log_new = False
    last_result = None
    with polling_values.transact() as tx:
        if tx.value.last_ops_result is None or result.has_different_content_than(
            tx.value.last_ops_result
        ):
            last_result = tx.value.last_ops_result
            log_new = True
            tx.value.need_line_break = False
            tx.value.last_ops_result = result
        else:
            tx.value.need_line_break = True
        need_line_break = tx.value.need_line_break

    log_entry = PollOperationalIntents(
        poll=result, recorded_at=StringBasedDateTime(arrow.utcnow())
    )
    if log_new:
        logger.log_new(log_entry)
        if need_line_break:
            print()
        print(diff.entity_diff_text(last_result, result))
    else:
        logger.log_same(t0, t1, log_entry.prefix_code())
        print_no_newline(".")


def poll_constraints(
    area: ObservationArea, scd_client: UTMClientSession, logger: tracerlog.Logger
) -> None:
    if not area.area.time_start or not area.area.time_end:
        return

    box = make_latlng_rect(area.area.volume)
    t0 = datetime.datetime.now(datetime.UTC)
    if "constraints" not in context.scd_cache:
        context.scd_cache["constraints"] = {}
    result = fetch_scd_constraints(
        scd_client,
        box,
        area.area.time_start.datetime,
        area.area.time_end.datetime,
        constraint_cache=context.scd_cache["constraints"],
    )
    t1 = datetime.datetime.now(datetime.UTC)

    log_new = False
    last_result = None
    with polling_values.transact() as tx:
        if result.has_different_content_than(tx.value.last_constraints_result):
            last_result = tx.value.last_constraints_result
            log_new = True
            tx.value.need_line_break = False
            tx.value.last_constraints_result = result
        else:
            tx.value.need_line_break = True
        need_line_break = tx.value.need_line_break

    log_entry = PollConstraints(
        poll=result, recorded_at=StringBasedDateTime(arrow.utcnow())
    )
    if log_new:
        logger.log_new(log_entry)
        if need_line_break:
            print()
        print(diff.entity_diff_text(last_result, result))
    else:
        logger.log_same(t0, t1, log_entry.prefix_code())
        print_no_newline(".")
