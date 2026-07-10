#!env/bin/python3

import argparse
import json
import os
import sys

from implicitdict import ImplicitDict
from loguru import logger

from monitoring.benchmarker.configurations.configuration import BenchmarkConfiguration
from monitoring.benchmarker.validation import validate_config
from monitoring.uss_qualifier.fileio import (
    load_dict_with_references,
)  # TODO: factor fileio out of uss_qualifier into monitorlib


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute benchmarker")

    parser.add_argument(
        "--config",
        help="Configuration string indicating file reference (e.g. file://path/to/config.jsonnet)",
        required=True,
    )

    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="If specified, do not validate the format of the provided configuration.",
    )

    return parser.parse_args()


def run_config(
    config_name: str,
    skip_validation: bool,
) -> int:
    config_src = load_dict_with_references(config_name)

    if not skip_validation:
        logger.info("Validating configuration...")
        validation_errors = validate_config(config_src)
        if validation_errors:
            for e in validation_errors:
                logger.error("[{}]: {}", e.json_path, e.message)
            raise ValueError(
                f"{len(validation_errors)} benchmark configuration validation errors indicated above.  Hint: resolve the clearest error first and then rerun validation."
            )

    whole_config = ImplicitDict.parse(config_src, BenchmarkConfiguration)

    # Print the resolved configuration to console as JSON
    print(json.dumps(whole_config, indent=2, sort_keys=True))

    return os.EX_OK


def main() -> int:
    args = parseArgs()

    logger.info(
        f"========== Running benchmarker for configuration {args.config} =========="
    )
    exit_code = run_config(
        args.config,
        args.skip_validation,
    )
    if exit_code != os.EX_OK:
        return exit_code
    logger.info(
        f"========== Completed benchmarker for configuration {args.config} =========="
    )

    return os.EX_OK


if __name__ == "__main__":
    sys.exit(main())
