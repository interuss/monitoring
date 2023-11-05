#!env/bin/python3

import argparse
import os
import sys

from implicitdict import ImplicitDict
from loguru import logger

from monitoring.uss_qualifier.configurations.configuration import (
    USSQualifierConfiguration,
    USSQualifierConfigurationV1,
)
from monitoring.uss_qualifier.fileio import load_dict_with_references
from monitoring.uss_qualifier.reports.artifacts import generate_artifacts
from monitoring.uss_qualifier.reports.report import TestRunReport, redact_access_tokens


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate artifacts from USS Qualifier report"
    )

    parser.add_argument(
        "--config",
        help="Configuration string according to monitoring/uss_qualifier/configurations/README.md; Several comma-separated strings may be specified",
        required=True,
    )

    parser.add_argument(
        "--report",
        help="File name of the report to read; Several comma-separated file names matching the configurations may be specified",
        required=True,
    )

    return parser.parse_args()


def main() -> int:
    args = parseArgs()

    config_names = str(args.config).split(",")

    report_paths = str(args.report).split(",")
    if len(report_paths) != len(config_names):
        raise ValueError(
            f"Need matching number of report, expected {len(config_names)}, got {len(report_paths)}"
        )

    for idx, config_name in enumerate(config_names):
        logger.info(
            f"========== Generating artifacts for configuration {config_name} =========="
        )

        config_src = load_dict_with_references(config_name)
        whole_config = ImplicitDict.parse(config_src, USSQualifierConfiguration)

        report_src = load_dict_with_references(report_paths[idx])
        report = ImplicitDict.parse(report_src, TestRunReport)

        config: USSQualifierConfigurationV1 = whole_config.v1
        if config.artifacts:
            generate_artifacts(report, config.artifacts)
        else:
            logger.warning(f"No artifacts to generate for {config_name}")

        logger.info(
            f"========== Completed generating artifacts for configuration {config_name} =========="
        )

    return os.EX_OK


if __name__ == "__main__":
    sys.exit(main())
