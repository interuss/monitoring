import math
from typing import List, Optional, Union

import s2sphere
from pykml.factory import KML_ElementMaker as kml

from monitoring.monitorlib.geo import (
    METERS_PER_FOOT,
    Altitude,
    AltitudeDatum,
    DistanceUnits,
    Radius,
    egm96_geoid_offset,
)
from monitoring.monitorlib.geotemporal import Volume4D

# Hexadecimal colors
GREEN = "ff00c000"
YELLOW = "ff00ffff"
RED = "ff0000ff"
CYAN = "ffc0c000"
TRANSLUCENT_GRAY = "80808080"
TRANSLUCENT_LIGHTGRAY = "80c0c0c0"
TRANSLUCENT_GREEN = "8000ff00"
TRANSLUCENT_LIGHTGREEN = "8040c040"
TRANSLUCENT_LIGHT_CYAN = "80ffffaa"
TRANSLUCENT_RED = "80ff0000ff"
TRANSLUCENT_YELLOW = "8000ffff"
TRANSPARENT = "00000000"


def _altitude_mode_of(altitude: Altitude) -> str:
    if altitude.reference == AltitudeDatum.W84:
        return "absolute"
    elif altitude.reference == AltitudeDatum.SFC:
        return "relativeToGround"
    else:
        raise NotImplementedError(
            f"Altitude reference {altitude.reference} not yet supported"
        )


def _distance_value_of(distance: Union[Altitude, Radius]) -> float:
    if distance.units == DistanceUnits.M:
        return distance.value
    elif distance.units == DistanceUnits.FT:
        return distance.value * METERS_PER_FOOT
    else:
        raise NotImplementedError(f"Distance units {distance.units} not yet supported")


def make_placemark_from_volume(
    v4: Volume4D,
    name: Optional[str] = None,
    style_url: Optional[str] = None,
    description: Optional[str] = None,
) -> kml.Placemark:
    if "outline_polygon" in v4.volume and v4.volume.outline_polygon:
        vertices = v4.volume.outline_polygon.vertices
    elif "outline_circle" in v4.volume and v4.volume.outline_circle:
        center = v4.volume.outline_circle.center
        r = _distance_value_of(v4.volume.outline_circle.radius)
        N_VERTICES = 32
        vertices = [
            center.offset(
                r * math.sin(2 * math.pi * theta / N_VERTICES),
                r * math.cos(2 * math.pi * theta / N_VERTICES),
            )
            for theta in range(0, N_VERTICES)
        ]
    else:
        raise NotImplementedError("Volume footprint type not supported")

    # Create placemark
    args = []
    if name is not None:
        args.append(kml.name(name))
    if style_url is not None:
        args.append(kml.styleUrl(style_url))
    placemark = kml.Placemark(*args)
    if description:
        placemark.append(kml.description(description))

    # Set time range
    timespan = None
    if "time_start" in v4 and v4.time_start:
        timespan = kml.TimeSpan(kml.begin(v4.time_start.datetime.isoformat()))
    if "time_end" in v4 and v4.time_end:
        if timespan is None:
            timespan = kml.TimeSpan()
        timespan.append(kml.end(v4.time_end.datetime.isoformat()))
    if timespan is not None:
        placemark.append(timespan)

    # Create top and bottom of the volume
    avg = s2sphere.LatLng.from_degrees(
        lat=sum(v.lat for v in vertices) / len(vertices),
        lng=sum(v.lng for v in vertices) / len(vertices),
    )
    geoid_offset = egm96_geoid_offset(avg)
    lower_coords = []
    upper_coords = []
    alt_lo = (
        _distance_value_of(v4.volume.altitude_lower) - geoid_offset
        if v4.volume.altitude_lower
        else 0
    )
    alt_hi = (
        _distance_value_of(v4.volume.altitude_upper) - geoid_offset
        if v4.volume.altitude_upper
        else 0
    )
    for vertex in vertices:
        lower_coords.append((vertex.lng, vertex.lat, alt_lo))
        upper_coords.append((vertex.lng, vertex.lat, alt_hi))
    geo = kml.MultiGeometry()
    make_sides = True
    if v4.volume.altitude_lower:
        geo.append(
            kml.Polygon(
                kml.altitudeMode(
                    _altitude_mode_of(
                        v4.volume.altitude_lower
                        if v4.volume.altitude_lower
                        else AltitudeDatum.SFC
                    )
                ),
                kml.outerBoundaryIs(
                    kml.LinearRing(
                        kml.coordinates(
                            " ".join(",".join(str(v) for v in c) for c in lower_coords)
                        )
                    )
                ),
            )
        )
    else:
        make_sides = False
    if v4.volume.altitude_upper:
        geo.append(
            kml.Polygon(
                kml.altitudeMode(
                    _altitude_mode_of(
                        v4.volume.altitude_upper
                        if v4.volume.altitude_upper
                        else AltitudeDatum.SFC
                    )
                ),
                kml.outerBoundaryIs(
                    kml.LinearRing(
                        kml.coordinates(
                            " ".join(",".join(str(v) for v in c) for c in upper_coords)
                        )
                    )
                ),
            )
        )
    else:
        make_sides = False

    # We can only create the sides of the volume if the altitude references are the same
    if (
        make_sides
        and v4.volume.altitude_lower.reference == v4.volume.altitude_upper.reference
    ):
        indices = list(range(len(vertices)))
        for i1, i2 in zip(indices, indices[1:] + [0]):
            coords = [
                (vertices[i1].lng, vertices[i1].lat, alt_lo),
                (vertices[i1].lng, vertices[i1].lat, alt_hi),
                (vertices[i2].lng, vertices[i2].lat, alt_hi),
                (vertices[i2].lng, vertices[i2].lat, alt_lo),
            ]
            geo.append(
                kml.Polygon(
                    kml.altitudeMode(_altitude_mode_of(v4.volume.altitude_lower)),
                    kml.outerBoundaryIs(
                        kml.LinearRing(
                            kml.coordinates(
                                " ".join(",".join(str(v) for v in c) for c in coords)
                            )
                        )
                    ),
                )
            )

    placemark.append(geo)
    return placemark


def query_styles() -> List[kml.Style]:
    """Provides KML styles for query areas."""
    return [
        kml.Style(
            kml.LineStyle(kml.color(CYAN), kml.width(3)),
            kml.PolyStyle(kml.color(TRANSLUCENT_LIGHT_CYAN)),
            id="QueryArea",
        ),
    ]
