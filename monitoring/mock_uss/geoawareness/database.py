import json

from implicitdict import ImplicitDict
from uas_standards.eurocae_ed269 import ED269Schema
from uas_standards.interuss.automated_testing.geo_awareness.v1.api import (
    CreateGeozoneSourceRequest,
    GeozoneSourceResponseResult,
)

from monitoring.monitorlib.multiprocessing import SynchronizedValue


class ExistingRecordException(ValueError):
    pass


class SourceRecord(ImplicitDict):
    definition: CreateGeozoneSourceRequest
    state: GeozoneSourceResponseResult
    message: str | None
    geozone_ed269: ED269Schema | None


class Database(ImplicitDict):
    """Simple pseudo-database structure tracking the state of the mock system"""

    sources: dict[str, SourceRecord] = {}


def get_source(
    geo_db: SynchronizedValue[Database], source_id: str
) -> SourceRecord | None:
    return geo_db.value.sources.get(source_id, None)


def get_sources(geo_db: SynchronizedValue[Database]) -> dict[str, SourceRecord]:
    return geo_db.value.sources


def insert_source(
    geo_db: SynchronizedValue[Database],
    source_id: str,
    definition: CreateGeozoneSourceRequest,
    state: GeozoneSourceResponseResult,
    message: str | None = None,
) -> SourceRecord:
    with geo_db.transact() as tx:
        if source_id in tx.value.sources.keys():
            raise ExistingRecordException()
        tx.value.sources[source_id] = SourceRecord(
            definition=definition, state=state, message=message
        )
        result = tx.value.sources[source_id]
    return result


def update_source_state(
    geo_db: SynchronizedValue[Database],
    source_id: str,
    state: GeozoneSourceResponseResult,
    message: str | None = None,
):
    with geo_db.transact() as tx:
        tx.value.sources[source_id]["state"] = state
        tx.value.sources[source_id]["message"] = message
        result = tx.value.sources[source_id]
    return result


def update_source_geozone_ed269(
    geo_db: SynchronizedValue[Database], source_id: str, geozone: ED269Schema
):
    with geo_db.transact() as tx:
        tx.value.sources[source_id]["geozone_ed269"] = geozone
        result = tx.value.sources[source_id]
    return result


def delete_source(geo_db: SynchronizedValue[Database], source_id: str):
    with geo_db.transact() as tx:
        return tx.value.sources.pop(source_id, None)


db = SynchronizedValue[Database](
    Database(),
    decoder=lambda b: ImplicitDict.parse(json.loads(b.decode("utf-8")), Database),
)
