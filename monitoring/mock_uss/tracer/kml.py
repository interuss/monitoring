from __future__ import annotations

import glob
import os
import re
from abc import abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Protocol, TypeVar

import yaml
from implicitdict import ImplicitDict
from loguru import logger
from lxml import etree
from pykml.factory import KML_ElementMaker as kml
from pykml.util import format_xml_with_cdata
from uas_standards.astm.f3548.v21.api import (
    GetOperationalIntentDetailsResponse,
    OperationalIntent,
    PutOperationalIntentDetailsParameters,
)

from monitoring.mock_uss.tracer.log_types import (
    OperationalIntentNotification,
    PollOperationalIntents,
    TracerLogEntry,
)
from monitoring.monitorlib.geotemporal import Volume4D, Volume4DCollection
from monitoring.monitorlib.infrastructure import get_token_claims
from monitoring.monitorlib.kml.f3548v21 import f3548v21_styles
from monitoring.monitorlib.kml.generation import make_placemark_from_volume
from monitoring.monitorlib.temporal import Time


class Stopwatch:
    _start_time: datetime | None = None
    elapsed_time: timedelta = timedelta(seconds=0)

    def __enter__(self):
        self._start_time = datetime.now(UTC)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._start_time:
            self.elapsed_time += datetime.now(UTC) - self._start_time


class VolumeType(str, Enum):
    OperationalIntent = "OperationalIntent"


@dataclass
class HistoricalVolumesCollection:
    type: VolumeType
    name: str
    version: str
    state: str
    volumes: Volume4DCollection
    active_at: datetime


TracerLogEntryType = TypeVar("TracerLogEntryType", bound=TracerLogEntry)


class HistoricalVolumesRenderer[TracerLogEntryType](Protocol):
    @abstractmethod
    def __call__(
        self,
        log_entry: TracerLogEntryType,
        existing_volume_collections: list[HistoricalVolumesCollection],
    ) -> list[HistoricalVolumesCollection]:
        """Function that generates named collections of 4D volumes from a tracer log entry.

        Args:
            log_entry: Recorded log entry for which to generate 4D volumes.
            existing_volume_collections: Pre-existing historical volume collections.

        Returns: Collection of 4D volume collections.
        """
        raise NotImplementedError


@dataclass
class HistoricalVolumesRenderInfo:
    renderer: HistoricalVolumesRenderer
    log_entry_type: type[TracerLogEntry]


_historical_volumes_renderers: dict[
    type[TracerLogEntry], HistoricalVolumesRenderInfo
] = {}


def historical_volumes_renderer(log_entry_type: type[TracerLogEntry]):
    """Decorator to label a function that renders historical volumes for a tracer log entry.

    Decorated functions should follow the HistoricalVolumesRenderer Protocol.

    Args:
        log_entry_type: The type of tracer log entry the decorated function can render historical volumes for.
    """

    def register_renderer(func: HistoricalVolumesRenderer) -> HistoricalVolumesRenderer:
        _historical_volumes_renderers[log_entry_type] = HistoricalVolumesRenderInfo(
            renderer=func,
            log_entry_type=log_entry_type,
        )
        return func

    return register_renderer


def _op_intent_volumes(op_intent: OperationalIntent) -> Volume4DCollection:
    nominal_volumes = (
        op_intent.details.volumes
        if "volumes" in op_intent.details and op_intent.details.volumes
        else []
    )
    off_nominal_volumes = (
        op_intent.details.off_nominal_volumes
        if "off_nominal_volumes" in op_intent.details
        and op_intent.details.off_nominal_volumes
        else []
    )
    return Volume4DCollection(
        Volume4D.from_f3548v21(v) for v in nominal_volumes + off_nominal_volumes
    )


@historical_volumes_renderer(OperationalIntentNotification)
def _historical_volumes_op_intent_notification(
    log_entry: OperationalIntentNotification,
    existing_volume_collections: list[HistoricalVolumesCollection],
) -> list[HistoricalVolumesCollection]:
    try:
        if log_entry.request.json is None:
            raise ValueError("No json data in log entry")

        req = ImplicitDict.parse(
            log_entry.request.json, PutOperationalIntentDetailsParameters
        )
    except ValueError as e:
        logger.warning(
            f"Could not parse PutOperationalIntentDetailsParameters: {str(e)}"
        )
        return []
    assert isinstance(req, PutOperationalIntentDetailsParameters)

    claims = get_token_claims(log_entry.request.headers or {})
    manager = claims.get("sub", "[Unknown manager]")
    name = f"{manager} {req.operational_intent_id}"

    if "operational_intent" in req and req.operational_intent:
        version = f"v{req.operational_intent.reference.version} ({req.operational_intent.reference.ovn})"
        state = req.operational_intent.reference.state.value
        volumes = _op_intent_volumes(req.operational_intent)
        # TODO: Visually differentiate between nominal and off-nominal volumes
    else:
        version = "[deleted]"
        state = "Ended"
        volumes = Volume4DCollection()

    # See if this op intent version already has a volumes collection
    already_defined = False
    for hvc in existing_volume_collections:
        if hvc.name == name and hvc.version == version:
            already_defined = True
            break
    if already_defined:
        # TODO: Verify content is the same
        return []

    return [
        HistoricalVolumesCollection(
            type=VolumeType.OperationalIntent,
            name=name,
            version=version,
            state=state,
            volumes=volumes,
            active_at=log_entry.recorded_at.datetime,
        )
    ]


@historical_volumes_renderer(PollOperationalIntents)
def _historical_volumes_op_intent_poll(
    log_entry: PollOperationalIntents,
    existing_volume_collections: list[HistoricalVolumesCollection],
) -> list[HistoricalVolumesCollection]:
    hvcs: list[HistoricalVolumesCollection] = []
    current_op_intents = set()

    # Add newly-polled operational intents
    for op_intent_id, query in log_entry.poll.uss_queries.items():
        try:
            if query.json_result is None:
                raise ValueError("No json result in query")

            resp = ImplicitDict.parse(
                query.json_result, GetOperationalIntentDetailsResponse
            )
        except ValueError as e:
            logger.warning(
                f"Could not parse new GetOperationalIntentDetailsResponse: {str(e)}"
            )
            continue
        assert isinstance(resp, GetOperationalIntentDetailsResponse)

        name = f"{resp.operational_intent.reference.manager} {resp.operational_intent.reference.id}"
        version = f"v{resp.operational_intent.reference.version} ({resp.operational_intent.reference.ovn})"
        current_op_intents.add(name)

        # See if this op intent version already has a volumes collection
        already_defined = False
        for hvc in existing_volume_collections:
            if hvc.name == name and hvc.version == version:
                already_defined = True
                break
        if already_defined:
            # TODO: Verify content is the same
            continue

        volumes = _op_intent_volumes(resp.operational_intent)
        hvcs.append(
            HistoricalVolumesCollection(
                type=VolumeType.OperationalIntent,
                name=name,
                version=version,
                state=resp.operational_intent.reference.state,
                volumes=volumes,
                active_at=log_entry.recorded_at.datetime,
            )
        )

    # Remove any existing operational intents that no longer exist as of this poll
    for cached_op_intent_id, cached_query in log_entry.poll.cached_uss_queries.items():
        try:
            if cached_query.json_result is None:
                raise ValueError("No json result in query")

            resp = ImplicitDict.parse(
                cached_query.json_result, GetOperationalIntentDetailsResponse
            )
        except ValueError as e:
            logger.warning(
                f"Could not parse cached GetOperationalIntentDetailsResponse: {str(e)}"
            )
            continue
        assert isinstance(resp, GetOperationalIntentDetailsResponse)

        name = f"{resp.operational_intent.reference.manager} {resp.operational_intent.reference.id}"
        current_op_intents.add(name)
    has_deleted_entry = set()
    for hvc in existing_volume_collections:
        if hvc.version == "[deleted]":
            has_deleted_entry.add(hvc.name)
    for hvc in existing_volume_collections:
        if hvc.name not in current_op_intents:
            # This existing operational intent no longer exists as of this poll
            if hvc.name not in has_deleted_entry:
                hvcs.append(
                    HistoricalVolumesCollection(
                        type=VolumeType.OperationalIntent,
                        name=hvc.name,
                        version="[deleted]",
                        state="Ended",
                        volumes=Volume4DCollection([]),
                        active_at=log_entry.recorded_at.datetime,
                    )
                )
                has_deleted_entry.add(hvc.name)

    return hvcs


@dataclass
class StyledVolume:
    name: str
    volume: Volume4D
    style: str


@dataclass
class VolumesFolder:
    name: str
    volumes: list[StyledVolume]
    children: list[VolumesFolder]
    reference_time: Time | None = None

    def truncate(self, latest_time: Time) -> None:
        to_remove = []
        for v in self.volumes:
            if (
                v.volume.time_start
                and v.volume.time_start.datetime > latest_time.datetime
            ):
                to_remove.append(v)
            elif (
                v.volume.time_end and v.volume.time_end.datetime > latest_time.datetime
            ):
                v.volume.time_end = latest_time
        for v in to_remove:
            self.volumes.remove(v)
        for c in self.children:
            c.truncate(latest_time)

    def to_kml_folder(self):
        if self.reference_time:
            description = f"Relative to {self.reference_time}"
            folder = kml.Folder(kml.name(self.name), kml.description(description))
        else:
            folder = kml.Folder(kml.name(self.name))

        for v in self.volumes:
            name = v.name

            if self.reference_time:
                base_time = self.reference_time.datetime

                def dt(t: Time) -> int:
                    return round((t.datetime - base_time).total_seconds())

                name = f"{name} {dt(v.volume.time_start) if v.volume.time_start else '?'}s-{dt(v.volume.time_end) if v.volume.time_end else '?'}s"

            folder.append(
                make_placemark_from_volume(v.volume, name=name, style_url=v.style)
            )
        for f in self.children:
            folder.append(f.to_kml_folder())
        return folder


def _get_style(type: VolumeType, state: str, future: bool) -> str:
    if type == VolumeType.OperationalIntent:
        return f"F3548v21{state}{'Future' if future else ''}"
    else:
        raise NotImplementedError()


def render_historical_kml(log_folder: str) -> str:
    logger.debug("Rendering historical KML...")

    # Performance metrics
    loading_time = Stopwatch()
    parsing_time = Stopwatch()
    processing_time = Stopwatch()
    generation_time = Stopwatch()
    rendering_time = Stopwatch()

    historical_volume_collections: list[HistoricalVolumesCollection] = []
    log_files = glob.glob(os.path.join(log_folder, "*.yaml"))
    log_files.sort()
    for log_file in log_files:
        logger.debug(f"Processing {log_file}")

        if "nochange_queries" in log_file:
            continue  # This is a known case where we don't want to print a warning

        # See if this is actually a log entry
        filename = os.path.split(log_file)[-1]
        m = re.match(r"^(\d{6})_(\d\d)(\d\d)(\d\d)_(\d{6})_([^.]+)\.yaml$", filename)
        if not m:
            # File name does not match log entry format
            logger.warning(f"File name {filename} does not match log entry format")
            continue

        # Determine type of log entry
        prefix_code = m.group(6)
        log_entry_type = TracerLogEntry.entry_type_from_prefix(prefix_code)
        if not log_entry_type:
            # Can't determine a log entry type from the prefix
            logger.warning(
                f"Cannot determine log entry type from prefix_code `{prefix_code}`"
            )
            continue

        # See if we can render volumes of log entry
        if log_entry_type not in _historical_volumes_renderers:
            # We don't have an historical volume renderer for this log entry type
            logger.warning(
                f"No historical volume renderer for {log_entry_type.__name__} in {log_file}"
            )
            continue

        # Render log entry into historical volume collections
        with open(log_file) as f:
            try:
                with loading_time:
                    content = yaml.load(f, Loader=yaml.CLoader)
                with parsing_time:
                    log_entry = ImplicitDict.parse(content, log_entry_type)
            except ValueError as e:
                logger.warning(f"Skipping {filename} because of parse error: {str(e)}")
                continue
        with processing_time:
            historical_volume_collections.extend(
                _historical_volumes_renderers[log_entry_type].renderer(
                    log_entry, historical_volume_collections
                )
            )

    historical_volume_collections.sort(key=lambda hv: hv.active_at)

    # Render historical volume collections into a folder structure
    with generation_time:
        top_folder: dict[VolumeType, VolumesFolder] = {}
        for hvc in historical_volume_collections:
            if hvc.type not in top_folder:
                top_folder[hvc.type] = VolumesFolder(
                    name=hvc.type, volumes=[], children=[]
                )
            type_folder = top_folder[hvc.type]

            children = [f for f in type_folder.children if f.name == hvc.name]
            if not children:
                id_folder = VolumesFolder(name=hvc.name, volumes=[], children=[])
                type_folder.children.append(id_folder)
            else:
                id_folder = children[0]

            # Truncate time ranges of volumes in previous version(s)
            t_hvc = Time(hvc.active_at)
            id_folder.truncate(t_hvc)

            if not hvc.volumes:
                continue

            version_folder = VolumesFolder(name=hvc.version, volumes=[], children=[])
            id_folder.children.append(version_folder)

            active_folder = VolumesFolder(
                name="Active", reference_time=t_hvc, volumes=[], children=[]
            )
            future_folder = VolumesFolder(
                name="Future", reference_time=t_hvc, volumes=[], children=[]
            )
            version_folder.children.append(active_folder)
            version_folder.children.append(future_folder)

            for i, v in enumerate(hvc.volumes):
                if v.time_end and v.time_end.datetime <= hvc.active_at:
                    # This volume ended before the collection was declared, so it never actually existed
                    continue
                if v.time_start and v.time_start.datetime < hvc.active_at:
                    # Volume is declared in the past, but it's only visible starting now
                    v.time_start = t_hvc
                elif v.time_start and v.time_start.datetime > hvc.active_at:
                    # Add a "future" volume between when this volume was declared and its start time
                    future_v = Volume4D(v)
                    future_v.time_end = v.time_start
                    future_v.time_start = t_hvc
                    style = _get_style(hvc.type, hvc.state, True)
                    future_folder.volumes.append(StyledVolume(f"v{i}", future_v, style))
                style = _get_style(hvc.type, hvc.state, False)
                active_folder.volumes.append(StyledVolume(f"v{i}", v, style))

    with rendering_time:
        doc = kml.kml(
            kml.Document(
                *f3548v21_styles(),
                *[f.to_kml_folder() for f in top_folder.values()],
            )
        )
        result = etree.tostring(format_xml_with_cdata(doc), pretty_print=True).decode(
            "utf-8"
        )

    logger.debug(
        f"Completed render_historical_kml with {loading_time.elapsed_time.total_seconds():.2f}s load, {parsing_time.elapsed_time.total_seconds():.2f}s parse, {processing_time.elapsed_time.total_seconds():.2f}s process, {generation_time.elapsed_time.total_seconds():.2f}s generate, {rendering_time.elapsed_time.total_seconds():.2f}s render"
    )
    return result
