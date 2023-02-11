from typing import Any, Dict

import s2sphere

from monitoring.monitorlib import fetch
import monitoring.monitorlib.fetch.rid
import monitoring.monitorlib.fetch.scd
from monitoring.mock_uss.tracer.resources import ResourceSet


def indent(s: str, level: int) -> str:
    return "\n".join(" " * level + line for line in s.split("\n"))


def poll_rid_isas(resources: ResourceSet, box: s2sphere.LatLngRect) -> Any:
    return fetch.rid.isas(
        resources.dss_client, box, resources.start_time, resources.end_time
    )


def poll_scd_operations(resources: ResourceSet) -> Any:
    if "operational_intents" not in resources.scd_cache:
        resources.scd_cache["operational_intents"]: Dict[
            str, fetch.scd.FetchedEntity
        ] = {}
    return fetch.scd.operations(
        resources.dss_client,
        resources.area,
        resources.start_time,
        resources.end_time,
        operation_cache=resources.scd_cache["operational_intents"],
    )


def poll_scd_constraints(resources: ResourceSet) -> Any:
    if "constraints" not in resources.scd_cache:
        resources.scd_cache["constraints"]: Dict[str, fetch.scd.FetchedEntity] = {}
    return fetch.scd.constraints(
        resources.dss_client,
        resources.area,
        resources.start_time,
        resources.end_time,
        constraint_cache=resources.scd_cache["constraints"],
    )
