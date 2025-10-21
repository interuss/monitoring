import argparse
import os
import sys

from monitoring.mock_uss.tracer.kml import render_historical_kml


def main(log_folder: str, kml_file: str) -> int:
    kml_text = render_historical_kml(log_folder)
    with open(kml_file, "w") as f:
        f.write(kml_text)
    return os.EX_OK


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an historical KML based on a folder of tracer logs"
    )

    parser.add_argument(
        "--logfolder",
        type=str,
        default=None,
        help="Path to the folder containing tracer log files",
    )

    parser.add_argument(
        "--kmlfile", type=str, default=None, help="Path to the KML file to create"
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    sys.exit(main(args.logfolder, args.kmlfile))
