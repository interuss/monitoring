from typing import Any, Dict

import s2sphere

from monitoring.monitorlib import fetch
import monitoring.monitorlib.fetch.rid
import monitoring.monitorlib.fetch.scd
from monitoring.mock_uss.tracer.resources import ResourceSet
from monitoring.monitorlib.rid import RIDVersion


def indent(s: str, level: int) -> str:
    return "\n".join(" " * level + line for line in s.split("\n"))


def poll_rid_isas(
    resources: ResourceSet, box: s2sphere.LatLngRect, rid_version: RIDVersion
) -> Any:
    return fetch.rid.isas(
        box,
        resources.start_time,
        resources.end_time,
        rid_version,
        resources.dss_clients["rid"],
    )


def poll_scd_operations(resources: ResourceSet) -> Any:
    if "operational_intents" not in resources.scd_cache:
        resources.scd_cache["operational_intents"]: Dict[
            str, fetch.scd.FetchedEntity
        ] = {}
    return fetch.scd.operations(
        resources.dss_clients["scd"],
        resources.area,
        resources.start_time,
        resources.end_time,
        operation_cache=resources.scd_cache["operational_intents"],
    )


def poll_scd_constraints(resources: ResourceSet) -> Any:
    if "constraints" not in resources.scd_cache:
        resources.scd_cache["constraints"]: Dict[str, fetch.scd.FetchedEntity] = {}
    return fetch.scd.constraints(
        resources.dss_clients["scd"],
        resources.area,
        resources.start_time,
        resources.end_time,
        constraint_cache=resources.scd_cache["constraints"],
    )
