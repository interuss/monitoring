#!env/bin/python3

import argparse
import json
import os
import sys

import arrow
from lxml import etree
from pykml.factory import KML_ElementMaker as kml
from pykml.util import format_xml_with_cdata
import yaml

from implicitdict import ImplicitDict
from monitoring.monitorlib.kml import make_placemark_from_volume, flight_planning_styles
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

    return parser.parse_args()


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

    raw = load_dict_with_references(path)
    collection: FlightIntentCollection = ImplicitDict.parse(raw, FlightIntentCollection)
    flight_intents = collection.resolve()

    folders = []
    for name, template in flight_intents.items():
        flight_intent = template.resolve(times)
        folder = kml.Folder(kml.name(name))

        non_basic_info = json.loads(
            json.dumps(
                {k: v for k, v in flight_intent.items() if k != "basic_information"}
            )
        )
        if non_basic_info:
            folder.append(
                kml.Folder(
                    kml.name("Flight intent information"),
                    kml.description("<pre>" + yaml.dump(non_basic_info) + "</pre>"),
                )
            )

        basic_info = flight_intent.basic_information
        for i, v4 in enumerate(basic_info.area):
            placemark = make_placemark_from_volume(
                v4,
                name=f"{name}: volume {i}",
                style_url=f"#{basic_info.usage_state.value}_{basic_info.uas_state.value}",
            )
            folder.append(placemark)
        folders.append(folder)
    doc = kml.kml(
        kml.Document(
            *flight_planning_styles(),
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
