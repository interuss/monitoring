import argparse
import json
import os
import sys

from loguru import logger

from monitoring.mock_uss.tracer.export.usslogset import make_usslogset


def main(log_folder: str, output_file: str) -> int:
    log_set = make_usslogset(log_folder)
    logger.info(
        f"Writing USSLogSet ({len(log_set.messages or [])} messages) to {output_file}"
    )
    with open(output_file, "w") as f:
        json.dump(log_set, f, indent=2, sort_keys=True)
    return os.EX_OK


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an ASTM F3548-21 USSLogSet JSON file from a folder of tracer logs"
    )

    parser.add_argument(
        "-l",
        "--log-folder",
        "--logfolder",
        dest="log_folder",
        type=str,
        required=True,
        help="Path to the folder containing tracer log files",
    )

    parser.add_argument(
        "-o",
        "--output",
        "--usslogset",
        dest="output_file",
        type=str,
        required=True,
        help="Path to the USSLogSet JSON file to create",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    sys.exit(main(args.log_folder, args.output_file))
