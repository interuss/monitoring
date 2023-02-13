import datetime
import json
import sys
from typing import Optional

from implicitdict import ImplicitDict
from monitoring.monitorlib import versioning
from monitoring.mock_uss import webapp
from monitoring.mock_uss.tracer import diff, polling
from monitoring.mock_uss.tracer.resources import ResourceSet, get_options
from monitoring.monitorlib.fetch.rid import FetchedISAs
from monitoring.monitorlib.fetch.scd import FetchedEntities
from monitoring.monitorlib.multiprocessing import SynchronizedValue


TASK_POLL_ISAS = "tracer poll ISAs"
TASK_POLL_OPS = "tracer poll ops"
TASK_POLL_CONSTRAINTS = "tracer poll constraints"


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


def _log_poll_start(args, resources):
    init = False
    with polling_status as tx:
        if not tx.started:
            init = True
            tx.started = True
    if init:
        config = vars(args)
        config["code_version"] = versioning.get_code_version()
        resources.logger.log_new("poll_start", config)


@webapp.periodic_task(TASK_POLL_ISAS)
def poll_isas() -> datetime:
    args = get_options()
    if args.rid_isa_poll_interval == 0:
        # The user did not request ISA polling
        return datetime.datetime.max

    resources = ResourceSet.from_arguments(args)
    _log_poll_start(args, resources)

    log_name = "poll_isas"
    t0 = datetime.datetime.utcnow()
    result = polling.poll_rid_isas(resources, resources.area)
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
        resources.logger.log_new(log_name, result)
        if need_line_break:
            print()
        print(diff.isa_diff_text(last_result, result))
    else:
        resources.logger.log_same(t0, t1, log_name)
        print_no_newline(".")


@webapp.periodic_task(TASK_POLL_OPS)
def poll_ops() -> datetime:
    args = get_options()
    if args.scd_operation_poll_interval == 0:
        # The user did not request ops polling
        return datetime.datetime.max

    resources = ResourceSet.from_arguments(args)
    _log_poll_start(args, resources)

    log_name = "poll_ops"
    t0 = datetime.datetime.utcnow()
    result = polling.poll_scd_operations(resources)
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
        resources.logger.log_new(log_name, result)
        if need_line_break:
            print()
        print(diff.entity_diff_text(last_result, result))
    else:
        resources.logger.log_same(t0, t1, log_name)
        print_no_newline(".")


@webapp.periodic_task(TASK_POLL_CONSTRAINTS)
def poll_constraints() -> datetime:
    args = get_options()
    if args.scd_constraint_poll_interval == 0:
        # The user did not request ops polling
        return datetime.datetime.max

    resources = ResourceSet.from_arguments(args)
    _log_poll_start(args, resources)

    log_name = "poll_constraints"
    t0 = datetime.datetime.utcnow()
    result = polling.poll_scd_constraints(resources)
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
        resources.logger.log_new(log_name, result)
        if need_line_break:
            print()
        print(diff.entity_diff_text(last_result, result))
    else:
        resources.logger.log_same(t0, t1, log_name)
        print_no_newline(".")
