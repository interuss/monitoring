#!env/bin/python3

import argparse
import json
import os
import sys

import yaml
from loguru import logger

from monitoring.benchmarker.artifacts.generation import (
    default_output_path,
    generate_artifacts,
)
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
        "--config-output",
        default=None,
        help="If specified, write the configuration as parsed (potentially from multiple files) to the single file specified by this path",
    )

    parser.add_argument(
        "--exit-before-execution",
        action="store_true",
        help="If specified, only exit before benchmark execution begins.",
    )

    parser.add_argument(
        "-o",
        "--output",
        "--output-dir",
        dest="output_dir",
        default=None,
        help="Folder to which output artifacts should be written (default: monitoring/benchmarker/output/<name of config>)",
    )

    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="If specified, do not validate the format of the provided configuration.",
    )

    return parser.parse_args()


def run_config(
    config_name: str,
    config_output: str | None,
    skip_validation: bool,
    exit_before_execution: bool,
    output_dir: str,
) -> int:
    config = load_config(config_name, skip_validation)

    if config_output:
        logger.info("Writing flattened configuration to {}", config_output)
        if config_output.lower().endswith(".json"):
            with open(config_output, "w") as f:
                json.dump(config, f, indent=2, sort_keys=True)
        elif config_output.lower().endswith(".yaml"):
            with open(config_output, "w") as f:
                yaml.dump(json.loads(json.dumps(config)), f, sort_keys=True)
        else:
            raise ValueError(
                "Unsupported extension for --config-output; only .json or .yaml file paths may be specified"
            )

    if exit_before_execution:
        logger.info("Exiting because --exit-before-execution specified.")
        return os.EX_OK

    run_report = run_benchmark(config, output_dir)

    if "artifacts" in config and config.artifacts:
        logger.info("Generating configured artifacts...")
        generate_artifacts(config.artifacts, run_report, output_dir)
        logger.info("Artifact generation complete.")
    else:
        logger.warning("No artifacts specified in configuration.")

    return os.EX_OK


def main() -> int:
    args = parseArgs()

    output_dir = args.output_dir or default_output_path(args.config)

    logger.info(
        f"========== Running benchmarker for configuration {args.config} =========="
    )
    exit_code = run_config(
        args.config,
        args.config_output,
        args.skip_validation,
        args.exit_before_execution,
        output_dir,
    )
    if exit_code != os.EX_OK:
        return exit_code
    logger.info(
        f"========== Completed benchmarker for configuration {args.config} =========="
    )

    return os.EX_OK


if __name__ == "__main__":
    sys.exit(main())
