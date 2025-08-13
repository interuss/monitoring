#!env/bin/python3

import argparse
import os
import sys

from implicitdict import ImplicitDict
from loguru import logger

from monitoring import uss_qualifier as uss_qualifier_module
from monitoring.monitorlib import inspection
from monitoring.uss_qualifier.configurations.configuration import (
    USSQualifierConfiguration,
    USSQualifierConfigurationV1,
)
from monitoring.uss_qualifier.fileio import load_dict_with_references
from monitoring.uss_qualifier.reports.artifacts import (
    default_output_path,
    generate_artifacts,
)
from monitoring.uss_qualifier.reports.report import TestRunReport


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate artifacts from USS Qualifier report"
    )

    parser.add_argument(
        "--config",
        default=None,
        help="Configuration string according to monitoring/uss_qualifier/configurations/README.md; Several comma-separated strings may be specified",
    )

    parser.add_argument(
        "--report",
        help="File name of the report to read; Several comma-separated file names matching the configurations may be specified",
        required=True,
    )

    parser.add_argument(
        "--output-path",
        default=None,
        help="Path to folder where artifacts should be written.  If not specified, defaults to output/{CONFIG_NAME}",
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

    inspection.import_submodules(uss_qualifier_module)

    for config_name, report_path in zip(config_names, report_paths):
        logger.info(
            f"========== Generating artifacts for configuration {config_name} and report {report_path} =========="
        )

        report_src = load_dict_with_references(report_path)
        report = ImplicitDict.parse(report_src, TestRunReport)

        if config_name != config_in_report:
            config_src = load_dict_with_references(config_name)
            whole_config = ImplicitDict.parse(config_src, USSQualifierConfiguration)
        else:
            whole_config = report.configuration

        config: USSQualifierConfigurationV1 = whole_config.v1
        if config.artifacts:
            if args.output_path:
                output_path = args.output_path
            elif config_name == config_in_report:
                report_name, _ = os.path.splitext(os.path.split(report_path)[-1])
                output_path = default_output_path(report_name)
            else:
                output_path = default_output_path(config_name)
            generate_artifacts(report, config.artifacts, output_path, False)
        else:
            output_path = "nowhere"
            logger.warning(f"No artifacts to generate for {config_name}")

        logger.info(
            f"========== Wrote artifacts for configuration {config_name} to {os.path.abspath(output_path)} =========="
        )

    return os.EX_OK


if __name__ == "__main__":
    sys.exit(main())
