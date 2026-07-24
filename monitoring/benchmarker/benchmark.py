#!env/bin/python3

import argparse
import os
import sys

from loguru import logger

from monitoring.benchmarker.artifacts.generation import generate_artifacts
from monitoring.benchmarker.engine.engine import run_benchmark
from monitoring.benchmarker.validation import load_config


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute benchmarker")

    parser.add_argument(
        "--config",
        help="Configuration string indicating file reference (e.g. file://path/to/config.jsonnet)",
        required=True,
    )

    parser.add_argument(
        "-o",
        "--output",
        "--output-dir",
        dest="output_dir",
        default=os.path.join(os.path.dirname(__file__), "output"),
        help="Folder to which output artifacts should be written (default: monitoring/benchmarker/output)",
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
    output_dir: str,
) -> int:
    config = load_config(config_name, skip_validation)

    run_report = run_benchmark(config)

    if "artifacts" in config and config.artifacts:
        logger.info("Generating configured artifacts...")
        generate_artifacts(config.artifacts, run_report, output_dir)
        logger.info("Artifact generation complete.")
    else:
        logger.warning("No artifacts specified in configuration.")

    return os.EX_OK


def main() -> int:
    args = parseArgs()

    logger.info(
        f"========== Running benchmarker for configuration {args.config} =========="
    )
    exit_code = run_config(
        args.config,
        args.skip_validation,
        args.output_dir,
    )
    if exit_code != os.EX_OK:
        return exit_code
    logger.info(
        f"========== Completed benchmarker for configuration {args.config} =========="
    )

    return os.EX_OK


if __name__ == "__main__":
    sys.exit(main())
