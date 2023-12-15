from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict

from implicitdict import ImplicitDict, StringBasedTimeDelta
import s2sphere as s2sphere

from monitoring.monitorlib.transformations import Transformation
from uas_standards.astm.f3548.v21 import api as f3548v21
from uas_standards.interuss.automated_testing.flight_planning.v1 import api as fp_api
from uas_standards.interuss.automated_testing.scd.v1 import api as interuss_scd_api

from monitoring.monitorlib import geo
from monitoring.monitorlib.geo import LatLngPoint, Circle, Altitude, Volume3D, Polygon
from monitoring.monitorlib.temporal import TestTime, Time, TimeDuringTest


class Volume4DTemplate(ImplicitDict):
    outline_polygon: Optional[Polygon] = None
    """Polygonal 2D outline/footprint of the specified area.  May not be defined if outline_circle is defined."""

    outline_circle: Optional[Circle] = None
    """Circular outline/footprint of the specified area.  May not be defined if outline_polygon is defined."""

    start_time: Optional[TestTime] = None
    """The time at which the virtual user may start using the specified geospatial area for their flight.  May not be defined if duration and end_time are defined."""

    end_time: Optional[TestTime] = None
    """The time at which the virtual user will be finished using the specified geospatial area for their flight.  May not be defined if duration and start_time are defined."""

    duration: Optional[StringBasedTimeDelta] = None
    """If only one of start_time and end_time is specified, then the other time should be separated from the specified time by this amount.  May not be defined in both start_time and end_time are defined."""

    altitude_lower: Optional[Altitude] = None
    """The minimum altitude at which the virtual user will fly while using this volume for their flight."""

    altitude_upper: Optional[Altitude] = None
    """The maximum altitude at which the virtual user will fly while using this volume for their flight."""

    transformations: Optional[List[Transformation]] = None
    """If specified, transform this volume according to these transformations in order."""

    def resolve(self, times: Dict[TimeDuringTest, Time]) -> Volume4D:
        """Resolve Volume4DTemplate into concrete Volume4D."""
        # Make 3D volume
        kwargs = {}
        if self.outline_circle is not None:
            kwargs["outline_circle"] = self.outline_circle
        if self.outline_polygon is not None:
            kwargs["outline_polygon"] = self.outline_polygon
        if self.altitude_lower is not None:
            kwargs["altitude_lower"] = self.altitude_lower
        if self.altitude_upper is not None:
            kwargs["altitude_upper"] = self.altitude_upper
        volume = Volume3D(**kwargs)

        # Make 4D volume
        kwargs = {"volume": volume}

        if self.start_time is not None:
            time_start = self.start_time.resolve(times)
        else:
            time_start = None

        if self.end_time is not None:
            time_end = self.end_time.resolve(times)
        else:
            time_end = None

        if self.duration is not None:
            if time_start is not None and time_end is not None:
                raise ValueError(
                    "A Volume4DTemplate may not specify time_start, time_end, and duration as this over-determines the time span"
                )
            if time_start is None and time_end is None:
                raise ValueError(
                    "A Volume4DTemplate may not specify duration without either time_start or time_end as this under-determines the time span"
                )
            if time_start is None:
                time_start = Time(time_end.datetime - self.duration.timedelta)
            if time_end is None:
                time_end = Time(time_start.datetime + self.duration.timedelta)

        if time_start is not None:
            kwargs["time_start"] = time_start
        if time_end is not None:
            kwargs["time_end"] = time_end

        result = Volume4D(**kwargs)

        if self.transformations:
            for xform in self.transformations:
                result = result.transform(xform)

        return result


class Volume4D(ImplicitDict):
    """Generic representation of a 4D volume, usable across multiple standards and formats."""

    volume: Volume3D
    time_start: Optional[Time] = None
    time_end: Optional[Time] = None

    def offset_time(self, dt: timedelta) -> Volume4D:
        kwargs = {"volume": self.volume}
        if self.time_start:
            kwargs["time_start"] = self.time_start.offset(dt)
        if self.time_end:
            kwargs["time_end"] = self.time_end.offset(dt)
        return Volume4D(**kwargs)

    def transform(self, transformation: Transformation) -> Volume4D:
        kwargs = {k: v for k, v in self.items() if v is not None}
        kwargs["volume"] = self.volume.transform(transformation)
        return Volume4D(**kwargs)

    def intersects_vol4(self, vol4_2: Volume4D) -> bool:
        vol4_1 = self
        if vol4_1.time_end.datetime < vol4_2.time_start.datetime:
            return False
        if vol4_1.time_start.datetime > vol4_2.time_end.datetime:
            return False
        return self.volume.intersects_vol3(vol4_2.volume)

    @property
    def rect_bounds(self) -> s2sphere.LatLngRect:
        lat_min = 90
        lat_max = -90
        lng_min = 360
        lng_max = -360
        if self.volume.outline_polygon:
            for v in self.volume.outline_polygon.vertices:
                lat_min = min(lat_min, v.lat)
                lat_max = max(lat_max, v.lat)
                lng_min = min(lng_min, v.lng)
                lng_max = max(lng_max, v.lng)
        if self.volume.outline_circle:
            circle = self.volume.outline_circle
            if circle.radius.units != "M":
                raise NotImplementedError(
                    "Unsupported circle radius units: {}".format(circle.radius.units)
                )
            lat_radius = 360 * circle.radius.value / geo.EARTH_CIRCUMFERENCE_M
            lng_radius = (
                360
                * circle.radius.value
                / (geo.EARTH_CIRCUMFERENCE_M * math.cos(math.radians(lat_radius)))
            )
            lat_min = min(lat_min, circle.center.lat - lat_radius)
            lat_max = max(lat_max, circle.center.lat + lat_radius)
            lng_min = min(lng_min, circle.center.lng - lng_radius)
            lng_max = max(lng_max, circle.center.lng + lng_radius)
        p1 = s2sphere.LatLng.from_degrees(lat_min, lng_min)
        p2 = s2sphere.LatLng.from_degrees(lat_max, lng_max)
        return s2sphere.LatLngRect.from_point_pair(p1, p2)

    @staticmethod
    def from_values(
        t0: Optional[datetime] = None,
        t1: Optional[datetime] = None,
        alt0: Optional[float] = None,
        alt1: Optional[float] = None,
        circle: Optional[Circle] = None,
        polygon: Optional[Polygon] = None,
    ) -> Volume4D:
        kwargs = dict()
        if circle is not None:
            kwargs["outline_circle"] = circle
        if polygon is not None:
            kwargs["outline_polygon"] = polygon
        if alt0 is not None:
            kwargs["altitude_lower"] = Altitude.w84m(alt0)
        if alt1 is not None:
            kwargs["altitude_upper"] = Altitude.w84m(alt1)
        vol3 = Volume3D(**kwargs)
        kwargs = {"volume": vol3}
        if t0 is not None:
            kwargs["time_start"] = Time(t0)
        if t1 is not None:
            kwargs["time_end"] = Time(t1)
        return Volume4D(**kwargs)

    @staticmethod
    def from_f3548v21(vol: f3548v21.Volume4D) -> Volume4D:
        if not isinstance(vol, f3548v21.Volume4D) and isinstance(vol, dict):
            vol = ImplicitDict.parse(vol, f3548v21.Volume4D)
        kwargs = {"volume": Volume3D.from_f3548v21(vol.volume)}
        if "time_start" in vol and vol.time_start:
            kwargs["time_start"] = Time(vol.time_start.value)
        if "time_end" in vol and vol.time_end:
            kwargs["time_end"] = Time(vol.time_end.value)
        return Volume4D(**kwargs)

    @staticmethod
    def from_interuss_scd_api(vol: interuss_scd_api.Volume4D) -> Volume4D:
        # InterUSS SCD API is field-compatible with ASTM F3548-21
        return Volume4D.from_f3548v21(vol)

    def to_f3548v21(self) -> f3548v21.Volume4D:
        kwargs = {"volume": self.volume.to_f3548v21()}
        if "time_start" in self and self.time_start:
            kwargs["time_start"] = self.time_start.to_f3548v21()
        if "time_end" in self and self.time_end:
            kwargs["time_end"] = self.time_end.to_f3548v21()
        return f3548v21.Volume4D(**kwargs)

    def to_interuss_scd_api(self) -> interuss_scd_api.Volume4D:
        # InterUSS SCD API is field-compatible with ASTM F3548-21
        return ImplicitDict.parse(self.to_f3548v21(), interuss_scd_api.Volume4D)

    @staticmethod
    def from_flight_planning_api(vol: fp_api.Volume4D):
        if "time_start" in vol and vol.time_start:
            t_start = Time(vol.time_start.value)
        else:
            t_start = None
        if "time_end" in vol and vol.time_end:
            t_end = Time(vol.time_end.value)
        else:
            t_end = None
        return Volume4D(
            volume=Volume3D.from_flight_planning_api(vol.volume),
            time_start=t_start,
            time_end=t_end,
        )

    def to_flight_planning_api(self) -> fp_api.Volume4D:
        kwargs = {"volume": self.volume.to_flight_planning_api()}
        if self.time_start:
            kwargs["time_start"] = fp_api.Time(value=self.time_start)
        if self.time_end:
            kwargs["time_end"] = fp_api.Time(value=self.time_end)
        return fp_api.Volume4D(**kwargs)


class Volume4DCollection(List[Volume4D]):
    def __add__(self, other):
        if isinstance(other, Volume4D):
            full_list = []
            full_list.extend(self)
            full_list.append(other)
            return Volume4DCollection(full_list)
        elif isinstance(other, Volume4DCollection):
            full_list = []
            full_list.extend(self)
            full_list.extend(other)
            return Volume4DCollection(full_list)
        else:
            raise NotImplementedError(
                f"Cannot add {type(other).__name__} to {type(self).__name__}"
            )

    def __iadd__(self, other):
        if isinstance(other, Volume4D):
            self.append(other)
        elif isinstance(other, Volume4DCollection):
            self.extend(other)
        else:
            raise NotImplementedError(
                f"Cannot iadd {type(other).__name__} to {type(self).__name__}"
            )

    @property
    def time_start(self) -> Optional[Time]:
        return (
            Time(min(v.time_start.datetime for v in self))
            if all("time_start" in v and v.time_start for v in self)
            else None
        )

    @property
    def time_end(self) -> Optional[Time]:
        return (
            Time(max(v.time_end.datetime for v in self))
            if all("time_end" in v and v.time_end for v in self)
            else None
        )

    def offset_times(self, dt: timedelta) -> Volume4DCollection:
        return Volume4DCollection([v.offset_time(dt) for v in self])

    @property
    def rect_bounds(self) -> s2sphere.LatLngRect:
        if not self:
            raise ValueError(
                "Cannot compute rectangular bounds when no volumes are present"
            )
        lat_min = math.inf
        lat_max = -math.inf
        lng_min = math.inf
        lng_max = -math.inf
        for vol4 in self:
            if "outline_polygon" in vol4.volume and vol4.volume.outline_polygon:
                for v in vol4.volume.outline_polygon.vertices:
                    lat_min = min(lat_min, v.lat)
                    lat_max = max(lat_max, v.lat)
                    lng_min = min(lng_min, v.lng)
                    lng_max = max(lng_max, v.lng)
            if "outline_circle" in vol4.volume and vol4.volume.outline_circle:
                circle = vol4.volume.outline_circle
                if circle.radius.units != "M":
                    raise NotImplementedError(
                        "Unsupported circle radius units: {}".format(
                            circle.radius.units
                        )
                    )
                lat_radius = 360 * circle.radius.value / geo.EARTH_CIRCUMFERENCE_M
                lng_radius = (
                    360
                    * circle.radius.value
                    / (geo.EARTH_CIRCUMFERENCE_M * math.cos(math.radians(lat_radius)))
                )
                lat_min = min(lat_min, circle.center.lat - lat_radius)
                lat_max = max(lat_max, circle.center.lat + lat_radius)
                lng_min = min(lng_min, circle.center.lng - lng_radius)
                lng_max = max(lng_max, circle.center.lng + lng_radius)
        p1 = s2sphere.LatLng.from_degrees(lat_min, lng_min)
        p2 = s2sphere.LatLng.from_degrees(lat_max, lng_max)
        return s2sphere.LatLngRect.from_point_pair(p1, p2)

    @property
    def bounding_volume(self) -> Volume4D:
        v_min, v_max = self.meter_altitude_bounds
        rect_bound = self.rect_bounds
        lat_lo = rect_bound.lat_lo().degrees
        lng_lo = rect_bound.lng_lo().degrees
        lat_hi = rect_bound.lat_hi().degrees
        lng_hi = rect_bound.lng_hi().degrees
        kwargs = {
            "volume": Volume3D(
                altitude_lower=Altitude.w84m(v_min),
                altitude_upper=Altitude.w84m(v_max),
                outline_polygon=Polygon(
                    vertices=[
                        LatLngPoint(lat=lat_lo, lng=lng_lo),
                        LatLngPoint(lat=lat_hi, lng=lng_lo),
                        LatLngPoint(lat=lat_hi, lng=lng_hi),
                        LatLngPoint(lat=lat_lo, lng=lng_hi),
                    ]
                ),
            )
        }
        if self.time_start is not None:
            kwargs["time_start"] = self.time_start
        if self.time_end is not None:
            kwargs["time_end"] = self.time_end
        return Volume4D(**kwargs)

    @property
    def meter_altitude_bounds(self) -> Tuple[float, float]:
        alt_lo = min(
            vol4.volume.altitude_lower.value
            for vol4 in self
            if "altitude_lower" in vol4.volume
        )
        alt_hi = max(
            vol4.volume.altitude_upper.value
            for vol4 in self
            if "altitude_upper" in vol4.volume
        )
        units = [
            vol4.volume.altitude_lower.units
            for vol4 in self
            if "altitude_lower" in vol4.volume
            and vol4.volume.altitude_lower.units != "M"
        ]
        if units:
            raise NotImplementedError(
                f"altitude_lower units must currently be M; found instead {', '.join(units)}"
            )
        units = [
            vol4.volume.altitude_upper.units
            for vol4 in self
            if "altitude_upper" in vol4.volume
            and vol4.volume.altitude_upper.units != "M"
        ]
        if units:
            raise NotImplementedError(
                f"altitude_upper units must currently be M; found instead {', '.join(units)}"
            )
        return alt_lo, alt_hi

    def intersects_vol4s(self, vol4s_2: Volume4DCollection) -> bool:
        for v1 in self:
            for v2 in vol4s_2:
                if v1.intersects_vol4(v2):
                    return True
        return False

    @staticmethod
    def from_f3548v21(vol4s: List[f3548v21.Volume4D]) -> Volume4DCollection:
        volumes = [Volume4D.from_f3548v21(v) for v in vol4s]
        return Volume4DCollection(volumes)

    @staticmethod
    def from_interuss_scd_api(
        vol4s: List[interuss_scd_api.Volume4D],
    ) -> Volume4DCollection:
        volumes = [Volume4D.from_interuss_scd_api(v) for v in vol4s]
        return Volume4DCollection(volumes)

    def to_f3548v21(self) -> List[f3548v21.Volume4D]:
        return [v.to_f3548v21() for v in self]

    def to_interuss_scd_api(self) -> List[interuss_scd_api.Volume4D]:
        return [v.to_interuss_scd_api() for v in self]

    def has_active_volume(self, time_ref: datetime) -> bool:
        return any(
            vol.time_start.datetime <= time_ref <= vol.time_end.datetime for vol in self
        )


class Volume4DTemplateCollection(List[Volume4DTemplate]):
    pass
