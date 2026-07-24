#!env/bin/python3

import argparse
import os
import sys
from pathlib import Path

from implicitdict import ImplicitDict
from loguru import logger

from monitoring.benchmarker.artifacts.generation import (
    generate_artifacts,
)
from monitoring.benchmarker.reports.report import BenchmarkRunReport
from monitoring.benchmarker.validation import load_config
from monitoring.uss_qualifier.fileio import load_dict_with_references, resolve_filename


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate artifacts from benchmarker report"
    )

    parser.add_argument(
        "--config",
        default=None,
        help="Configuration string indicating file reference (e.g. file://path/to/config.jsonnet); Several comma-separated strings may be specified",
    )

    parser.add_argument(
        "--report",
        help="File name of the report to read; Several comma-separated file names matching the configurations may be specified",
        required=True,
    )

    parser.add_argument(
        "-o",
        "--output",
        "--output-dir",
        "--output-path",
        dest="output_path",
        default=None,
        help="Path to folder where artifacts should be written. If not specified, defaults to output/{CONFIG_NAME}",
    )

    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="If specified, do not validate the format of the provided configuration when loaded from --config.",
    )

    return parser.parse_args()


def main() -> int:
    args = parseArgs()

    report_paths = str(args.report).split(",")

    config_in_report = "<config in report>"
    if args.config:
        config_names = str(args.config).split(",")

        if len(report_paths) != len(config_names):
            raise ValueError(
                f"Need matching number of report, expected {len(config_names)}, got {len(report_paths)}"
            )
    else:
        config_names = [config_in_report] * len(report_paths)

    for config_name, report_path in zip(config_names, report_paths):
        logger.info(
            f"========== Generating artifacts for configuration {config_name} and report {report_path} =========="
        )

        if config_name != config_in_report:
            logger.debug("Loading config...")
            config = load_config(config_name, skip_validation=args.skip_validation)
        else:
            config = None

        logger.debug("Loading report...")
        report_src = load_dict_with_references(report_path)
        logger.debug("Parsing report...")
        report = ImplicitDict.parse(report_src, BenchmarkRunReport)

        if config is None:
            config = report.configuration

        if "artifacts" in config and config.artifacts:
            logger.debug("Generating artifacts...")
            if args.output_path:
                output_path = args.output_path
            else:
                output_path = str(Path(resolve_filename(report_path)).parent)
            generate_artifacts(config.artifacts, report, output_path)
        else:
            output_path = "nowhere"
            logger.warning(f"No artifacts to generate for {config_name}")

        logger.info(
            f"========== Wrote artifacts for configuration {config_name} to {os.path.abspath(output_path)} =========="
        )

    return os.EX_OK


if __name__ == "__main__":
    sys.exit(main())
