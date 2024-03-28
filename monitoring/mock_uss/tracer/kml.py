from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import glob
import os
import re
from enum import Enum
from typing import Protocol, Dict, Type, List

from loguru import logger
from lxml import etree
from pykml.factory import KML_ElementMaker as kml
from pykml.util import format_xml_with_cdata
import yaml

from implicitdict import ImplicitDict, StringBasedDateTime
from monitoring.mock_uss.tracer.log_types import (
    TracerLogEntry,
    OperationalIntentNotification,
)
from monitoring.monitorlib.geotemporal import Volume4DCollection, Volume4D
from monitoring.monitorlib.kml.f3548v21 import f3548v21_styles
from monitoring.monitorlib.kml.generation import make_placemark_from_volume
from monitoring.monitorlib.temporal import Time
from uas_standards.astm.f3548.v21.api import PutOperationalIntentDetailsParameters


class VolumeType(str, Enum):
    OperationalIntent = "OperationalIntent"


@dataclass
class HistoricalVolumesCollection(object):
    type: VolumeType
    name: str
    version: str
    state: str
    volumes: Volume4DCollection
    active_at: datetime


class HistoricalVolumesRenderer(Protocol):
    def __call__(
        self, timestamp: datetime, log_entry: TracerLogEntry
    ) -> List[HistoricalVolumesCollection]:
        """Function that generates named collections of 4D volumes from a tracer log entry.

        Args:
            timestamp: Time at which log entry was recorded.
            log_entry: Recorded log entry for which to generate 4D volumes.

        Returns: Collection of 4D volume collections.
        """


@dataclass
class HistoricalVolumesRenderInfo(object):
    renderer: HistoricalVolumesRenderer
    log_entry_type: Type[TracerLogEntry]


_historical_volumes_renderers: Dict[
    Type[TracerLogEntry], HistoricalVolumesRenderInfo
] = {}


def historical_volumes_renderer(log_entry_type: Type[TracerLogEntry]):
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


@historical_volumes_renderer(OperationalIntentNotification)
def _historical_volumes_op_intent_notification(
    timestamp: datetime, log_entry: OperationalIntentNotification
) -> List[HistoricalVolumesCollection]:
    try:
        req = ImplicitDict.parse(
            log_entry.request.json, PutOperationalIntentDetailsParameters
        )
    except ValueError as e:
        logger.warning(
            f"Could not parse PutOperationalIntentDetailsParameters: {str(e)}"
        )
        return []
    assert isinstance(req, PutOperationalIntentDetailsParameters)

    if "operational_intent" in req and req.operational_intent:
        version = f"v{req.operational_intent.reference.version} ({req.operational_intent.reference.ovn})"
        state = req.operational_intent.reference.state.value
        nominal_volumes = (
            req.operational_intent.details.volumes
            if "volumes" in req.operational_intent.details
            and req.operational_intent.details.volumes
            else []
        )
        off_nominal_volumes = (
            req.operational_intent.details.off_nominal_volumes
            if "off_nominal_volumes" in req.operational_intent.details
            and req.operational_intent.details.off_nominal_volumes
            else []
        )
        volumes = Volume4DCollection(
            Volume4D.from_f3548v21(v) for v in nominal_volumes + off_nominal_volumes
        )
        # TODO: Visually differentiate between nominal and off-nominal volumes
    else:
        version = "[deleted]"
        state = "Ended"
        volumes = []

    return [
        HistoricalVolumesCollection(
            type=VolumeType.OperationalIntent,
            name=req.operational_intent_id,
            version=version,
            state=state,
            volumes=volumes,
            active_at=timestamp,
        )
    ]


@dataclass
class StyledVolume(object):
    volume: Volume4D
    style: str


@dataclass
class VolumesFolder(object):
    name: str
    volumes: List[StyledVolume]
    children: List[VolumesFolder]

    def to_kml_folder(self) -> kml.Folder:
        folder = kml.Folder(kml.name(self.name))
        for i, v in enumerate(self.volumes):
            folder.append(
                make_placemark_from_volume(
                    v.volume, name=f"Volume {i}", style_url=v.style
                )
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
    historical_volume_collections: List[HistoricalVolumesCollection] = []
    for log_file in glob.glob(os.path.join(log_folder, "*.yaml")):
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
                f"No historical volume renderer for {log_entry_type.__name__}"
            )
            continue

        # Render log entry into historical volume collections
        timestamp = StringBasedDateTime(
            datetime.utcnow().strftime("%Y-%m-%d")
            + f"T{m.group(2)}:{m.group(3)}:{m.group(4)}.{m.group(5)}Z"
        ).datetime
        with open(log_file, "r") as f:
            try:
                log_entry = ImplicitDict.parse(yaml.full_load(f), log_entry_type)
            except ValueError as e:
                logger.warning(f"Skipping {filename} because of parse error: {str(e)}")
                continue
        historical_volume_collections.extend(
            _historical_volumes_renderers[log_entry_type].renderer(timestamp, log_entry)
        )

    historical_volume_collections.sort(key=lambda hv: hv.active_at)

    top_folder: Dict[VolumeType, VolumesFolder] = {}
    for hvc in historical_volume_collections:
        if hvc.type not in top_folder:
            top_folder[hvc.type] = VolumesFolder(name=hvc.type, volumes=[], children=[])
        type_folder = top_folder[hvc.type]

        children = [f for f in type_folder.children if f.name == hvc.name]
        if not children:
            id_folder = VolumesFolder(name=hvc.name, volumes=[], children=[])
            type_folder.children.append(id_folder)
        else:
            id_folder = children[0]

        if id_folder.children:
            # Truncate time ranges of volumes in previous version
            for v in id_folder.children[-1].volumes:
                if v.volume.time_end.datetime > hvc.active_at:
                    v.volume.time_end = Time(hvc.active_at)

        version_folder = VolumesFolder(name=hvc.version, volumes=[], children=[])
        id_folder.children.append(version_folder)

        for v in hvc.volumes:
            if v.time_end.datetime <= hvc.active_at:
                # This volume ended before the collection was declared, so it never actually existed
                continue
            if v.time_start.datetime < hvc.active_at:
                v.time_start = Time(hvc.active_at)
            elif v.time_start.datetime > hvc.active_at:
                # Add a "future" volume between when this volume was declared and its start time
                future_v = Volume4D(v)
                future_v.time_end = v.time_start
                future_v.time_start = Time(hvc.active_at)
                style = _get_style(hvc.type, hvc.state, True)
                version_folder.volumes.append(StyledVolume(future_v, style))
            style = _get_style(hvc.type, hvc.state, False)
            version_folder.volumes.append(StyledVolume(v, style))

    doc = kml.kml(
        kml.Document(
            *f3548v21_styles(),
            *[f.to_kml_folder() for f in top_folder.values()],
        )
    )
    return etree.tostring(format_xml_with_cdata(doc), pretty_print=True).decode("utf-8")
