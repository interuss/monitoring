#!env/bin/python3

import argparse
import json
import os
import sys

import arrow
from loguru import logger
from lxml import etree
from pykml.factory import KML_ElementMaker as kml
from pykml.util import format_xml_with_cdata
import yaml

from implicitdict import ImplicitDict
from monitoring.monitorlib.geo import AltitudeDatum, Altitude, DistanceUnits
from monitoring.monitorlib.temporal import Time, TimeDuringTest
from monitoring.uss_qualifier.fileio import load_dict_with_references, resolve_filename
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntentCollection,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Produce a KML file showing a FlightIntentCollection"
    )

    parser.add_argument(
        "flight_intent_collection",
        help="Path to file containing FlightIntentCollection (*.yaml or *.json).  When using the file system, prefix with file://",
    )

    parser.add_argument(
        "--start_of_test_run",
        default=None,
        help="When start_of_test_run should be.  Defaults to now.",
    )

    parser.add_argument(
        "--geoid_offset",
        default=None,
        help="Height of the EGM96 geoid above the WGS84 ellipsoid in the area (meters).  Can be obtained as 'EGM96' at https://geographiclib.sourceforge.io/cgi-bin/GeoidEval",
    )

    return parser.parse_args()


def _altitude_mode_of(altitude: Altitude) -> str:
    if altitude.reference == AltitudeDatum.W84:
        return "absolute"
    else:
        raise NotImplementedError(
            f"Altitude reference {altitude.reference} not yet supported"
        )


def _altitude_value_of(altitude: Altitude) -> float:
    if altitude.units == DistanceUnits.M:
        return altitude.value
    else:
        raise NotImplementedError(f"Altitude units {altitude.units} not yet supported")


def main() -> int:
    args = parse_args()

    path = args.flight_intent_collection
    output_path = os.path.splitext(resolve_filename(path))[0] + ".kml"

    start_of_test_run = Time(args.start_of_test_run or arrow.utcnow().datetime)
    times = {
        TimeDuringTest.StartOfTestRun: start_of_test_run,
        TimeDuringTest.StartOfScenario: start_of_test_run,
        TimeDuringTest.TimeOfEvaluation: start_of_test_run,
    }
    if args.geoid_offset is None:
        logger.warning(
            "geoid_offset was not provided.  Assuming 0 offset, and this may cause altitude errors of up to tens of meters."
        )
        geoid_offset = 0
    else:
        geoid_offset = float(args.geoid_offset)

    raw = load_dict_with_references(path)
    collection: FlightIntentCollection = ImplicitDict.parse(raw, FlightIntentCollection)
    flight_intents = collection.resolve()

    folders = []
    for name, template in flight_intents.items():
        flight_intent = template.resolve(times)
        non_basic_info = json.loads(
            json.dumps(
                {k: v for k, v in flight_intent.items() if k != "basic_information"}
            )
        )
        description = yaml.dump(non_basic_info) if non_basic_info else None
        folder = kml.Folder(kml.name(name))
        basic_info = flight_intent.basic_information
        for i, v4 in enumerate(basic_info.area):
            if "outline_polygon" in v4.volume and v4.volume.outline_polygon:
                # Create placemark
                placemark = kml.Placemark(
                    kml.name(f"{name}: volume {i}"),
                    kml.styleUrl(
                        f"#{basic_info.usage_state.value}_{basic_info.uas_state.value}"
                    ),
                )
                if description:
                    placemark.append(kml.description("<pre>" + description + "</pre>"))

                # Set time range
                timespan = None
                if "time_start" in v4 and v4.time_start:
                    timespan = kml.TimeSpan(
                        kml.begin(v4.time_start.datetime.isoformat())
                    )
                if "time_end" in v4 and v4.time_end:
                    if timespan is None:
                        timespan = kml.TimeSpan()
                    timespan.append(kml.end(v4.time_end.datetime.isoformat()))
                if timespan is not None:
                    placemark.append(timespan)

                # Create top and bottom of the volume
                vertices = v4.volume.outline_polygon.vertices
                lower_coords = []
                upper_coords = []
                alt_lo = _altitude_value_of(v4.volume.altitude_lower) - geoid_offset
                alt_hi = _altitude_value_of(v4.volume.altitude_upper) - geoid_offset
                for vertex in vertices:
                    lower_coords.append((vertex.lng, vertex.lat, alt_lo))
                    upper_coords.append((vertex.lng, vertex.lat, alt_hi))
                geo = kml.MultiGeometry(
                    kml.Polygon(
                        kml.altitudeMode(_altitude_mode_of(v4.volume.altitude_lower)),
                        kml.outerBoundaryIs(
                            kml.LinearRing(
                                kml.coordinates(
                                    " ".join(
                                        ",".join(str(v) for v in c)
                                        for c in lower_coords
                                    )
                                )
                            )
                        ),
                    ),
                    kml.Polygon(
                        kml.altitudeMode(_altitude_mode_of(v4.volume.altitude_upper)),
                        kml.outerBoundaryIs(
                            kml.LinearRing(
                                kml.coordinates(
                                    " ".join(
                                        ",".join(str(v) for v in c)
                                        for c in upper_coords
                                    )
                                )
                            )
                        ),
                    ),
                )

                # We can only create the sides of the volume if the altitude references are the same
                if (
                    v4.volume.altitude_lower.reference
                    == v4.volume.altitude_upper.reference
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
                                kml.altitudeMode(
                                    _altitude_mode_of(v4.volume.altitude_lower)
                                ),
                                kml.outerBoundaryIs(
                                    kml.LinearRing(
                                        kml.coordinates(
                                            " ".join(
                                                ",".join(str(v) for v in c)
                                                for c in coords
                                            )
                                        )
                                    )
                                ),
                            )
                        )

                placemark.append(geo)
                folder.append(placemark)
            else:
                raise NotImplementedError("Volume footprint type not supported")
        folders.append(folder)
    doc = kml.kml(
        kml.Document(
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
            *folders,
        )
    )

    with open(output_path, "w") as f:
        f.write(
            etree.tostring(format_xml_with_cdata(doc), pretty_print=True).decode(
                "utf-8"
            )
        )

    return os.EX_OK


if __name__ == "__main__":
    sys.exit(main())
