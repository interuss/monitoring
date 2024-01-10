import math
import re
from typing import List, Optional, Union

import s2sphere
from pykml import parser
from pykml.factory import KML_ElementMaker as kml

from monitoring.monitorlib.geo import (
    Altitude,
    AltitudeDatum,
    DistanceUnits,
    egm96_geoid_offset,
    Radius,
    EARTH_CIRCUMFERENCE_M,
    LatLngPoint,
)
from monitoring.monitorlib.geotemporal import Volume4D

KML_NAMESPACE = {"kml": "http://www.opengis.net/kml/2.2"}
METERS_PER_FOOT = 0.3048


def get_kml_root(kml_obj, from_string=False):
    if from_string:
        content = parser.fromstring(kml_obj)
        return content
    content = parser.parse(kml_obj)
    return content.getroot()


def get_folders(root):
    return root.Document.Folder.Folder


def get_polygon_speed(polygon_name):
    """Returns speed unit within a polygon."""
    result = re.search(r"\(([0-9.]+)\)", polygon_name)
    return float(result.group(1)) if result else None


def get_folder_details(folder_elem):
    speed_polygons = {}
    alt_polygons = {}
    operator_location = {}
    coordinates = ""
    for placemark in folder_elem.xpath(".//kml:Placemark", namespaces=KML_NAMESPACE):
        placemark_name = str(placemark.name)
        polygons = placemark.xpath(".//kml:Polygon", namespaces=KML_NAMESPACE)

        if placemark_name == "operator_location":
            operator_point = folder_elem.xpath(
                ".//kml:Placemark/kml:Point/kml:coordinates", namespaces=KML_NAMESPACE
            )[0]
            if operator_point:
                operator_point = str(operator_point).split(",")
                operator_location = {"lng": operator_point[0], "lat": operator_point[1]}
        if polygons:
            if placemark_name.startswith("alt:"):
                polygon_coords = get_coordinates_from_kml(
                    polygons[0].outerBoundaryIs.LinearRing.coordinates
                )
                alt_polygons.update({placemark_name: polygon_coords})
            if placemark_name.startswith("speed:"):
                if not get_polygon_speed(placemark_name):
                    raise ValueError(
                        'Could not determine Polygon speed from Placemark "{}"'.format(
                            placemark_name
                        )
                    )
                polygon_coords = get_coordinates_from_kml(
                    polygons[0].outerBoundaryIs.LinearRing.coordinates
                )
                speed_polygons.update({placemark_name: polygon_coords})

        coords = placemark.xpath(
            ".//kml:LineString/kml:coordinates", namespaces=KML_NAMESPACE
        )
        if coords:
            coordinates = coords
            coordinates = get_coordinates_from_kml(coordinates)
    return {
        str(folder_elem.name): {
            "description": get_folder_description(folder_elem),
            "speed_polygons": speed_polygons,
            "alt_polygons": alt_polygons,
            "input_coordinates": coordinates,
            "operator_location": operator_location,
        }
    }


def get_coordinates_from_kml(coordinates):
    """Returns list of tuples of coordinates.
    Args:
        coordinates: coordinates element from KML.
    """
    if coordinates:
        return [
            tuple(float(x.strip()) for x in c.split(","))
            for c in str(coordinates[0]).split(" ")
            if c.strip()
        ]


def get_folder_description(folder_elem):
    """Returns folder description from KML.
    Args:
        folder_elem: Folder element from KML.
    """
    description = folder_elem.description
    lines = [line for line in str(description).split("\n") if ":" in line]
    values = {}
    for line in lines:
        cols = [col.strip() for col in line.split(":")]
        if len(cols) == 2:
            values[cols[0]] = cols[1]
    return values


def get_kml_content(kml_file, from_string=False):
    root = get_kml_root(kml_file, from_string)
    folders = get_folders(root)
    kml_content = {}
    for folder in folders:
        folder_details = get_folder_details(folder)
        if folder_details:
            kml_content.update(folder_details)
    return kml_content


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
        if "altitude_lower" in v4.volume
        else 0
    )
    alt_hi = (
        _distance_value_of(v4.volume.altitude_upper) - geoid_offset
        if "altitude_upper" in v4.volume
        else 0
    )
    for vertex in vertices:
        lower_coords.append((vertex.lng, vertex.lat, alt_lo))
        upper_coords.append((vertex.lng, vertex.lat, alt_hi))
    geo = kml.MultiGeometry()
    make_sides = True
    if "altitude_lower" in v4.volume:
        geo.append(
            kml.Polygon(
                kml.altitudeMode(
                    _altitude_mode_of(
                        v4.volume.altitude_lower
                        if "altitude_lower" in v4.volume
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
    if "altitude_upper" in v4.volume:
        geo.append(
            kml.Polygon(
                kml.altitudeMode(
                    _altitude_mode_of(
                        v4.volume.altitude_upper
                        if "altitude_upper" in v4.volume
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


def flight_planning_styles() -> List[kml.Style]:
    """Provides KML styles with names in the form {FlightPlanState}_{AirspaceUsageState}."""
    return [
        kml.Style(
            kml.LineStyle(kml.color("ff00c000"), kml.width(3)),
            kml.PolyStyle(kml.color("80808080")),
            id="Planned_Nominal",
        ),
        kml.Style(
            kml.LineStyle(kml.color("ff00c000"), kml.width(3)),
            kml.PolyStyle(kml.color("8000ff00")),
            id="InUse_Nominal",
        ),
        kml.Style(
            kml.LineStyle(kml.color("ff00ffff"), kml.width(5)),
            kml.PolyStyle(kml.color("8000ff00")),
            id="InUse_OffNominal",
        ),
        kml.Style(
            kml.LineStyle(kml.color("ff0000ff"), kml.width(5)),
            kml.PolyStyle(kml.color("8000ff00")),
            id="InUse_Contingent",
        ),
    ]


def query_styles() -> List[kml.Style]:
    """Provides KML styles for query areas."""
    return [
        kml.Style(
            kml.LineStyle(kml.color("ffc0c000"), kml.width(3)),
            kml.PolyStyle(kml.color("80ffffaa")),
            id="QueryArea",
        ),
    ]


def f3548v21_styles() -> List[kml.Style]:
    """Provides KML styles according to F3548-21 operational intent states."""
    return [
        kml.Style(
            kml.LineStyle(kml.color("ff00c000"), kml.width(3)),
            kml.PolyStyle(kml.color("80808080")),
            id="F3548v21Accepted",
        ),
        kml.Style(
            kml.LineStyle(kml.color("ff00c000"), kml.width(3)),
            kml.PolyStyle(kml.color("8000ff00")),
            id="F3548v21Activated",
        ),
        kml.Style(
            kml.LineStyle(kml.color("ff00ffff"), kml.width(5)),
            kml.PolyStyle(kml.color("8000ff00")),
            id="F3548v21Nonconforming",
        ),
        kml.Style(
            kml.LineStyle(kml.color("ff0000ff"), kml.width(5)),
            kml.PolyStyle(kml.color("8000ff00")),
            id="F3548v21Contingent",
        ),
    ]
