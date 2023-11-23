#!env/bin/python3

import argparse
import json
import os
import sys
from typing import Optional

from implicitdict import ImplicitDict
from loguru import logger
import yaml

from monitoring.monitorlib.dicts import remove_elements
from monitoring.monitorlib.versioning import get_code_version, get_commit_hash
from monitoring.uss_qualifier.configurations.configuration import (
    USSQualifierConfiguration,
    USSQualifierConfigurationV1,
)
from monitoring.uss_qualifier.fileio import load_dict_with_references
from monitoring.uss_qualifier.reports.artifacts import generate_artifacts
from monitoring.uss_qualifier.reports.report import TestRunReport
from monitoring.uss_qualifier.reports.validation.report_validation import (
    validate_report,
)
from monitoring.uss_qualifier.resources.resource import create_resources
from monitoring.uss_qualifier.signatures import (
    compute_signature,
    compute_baseline_signature,
)
from monitoring.uss_qualifier.suites.suite import TestSuiteAction, ExecutionContext
from monitoring.uss_qualifier.validation import validate_config


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute USS Qualifier")

    parser.add_argument(
        "--config",
        help="Configuration string according to monitoring/uss_qualifier/configurations/README.md; Several comma-separated strings may be specified",
        required=True,
    )

    parser.add_argument(
        "--config-output",
        default=None,
        help="If specified, write the configuration as parsed (potentially from multiple files) to the single file specified by this path; Several comma-separated file names matching the configurations may be specified",
    )

    parser.add_argument(
        "--exit-before-execution",
        action="store_true",
        help="If specified, only exit before test execution begins.",
    )

    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="If specified, do not validate the format of the provided configuration.",
    )

    parser.add_argument(
        "--output-path",
        default=None,
        help="If specified, override v1.artifacts.output_path with this value.  Overriding in this way does not change the test baseline.",
    )

    return parser.parse_args()


def execute_test_run(whole_config: USSQualifierConfiguration):
    config = whole_config.v1.test_run
    codebase_version = get_code_version()
    commit_hash = get_commit_hash()

    logger.info("Instantiating resources")
    resources = create_resources(config.resources.resource_declarations)

    logger.info("Computing signatures of inputs")
    if config.non_baseline_inputs:
        baseline, environment = remove_elements(
            whole_config, config.non_baseline_inputs
        )
    else:
        baseline = whole_config
        environment = []
    baseline_signature = compute_baseline_signature(
        codebase_version,
        commit_hash,
        compute_signature(baseline),
    )
    environment_signature = compute_signature(environment)

    logger.info("Instantiating top-level test suite action")
    context = ExecutionContext(config.execution if "execution" in config else None)
    action = TestSuiteAction(config.action, resources)
    logger.info("Running top-level test suite action")
    report = action.run(context)
    if report.successful():
        logger.info("Final result: SUCCESS")
    else:
        logger.warning("Final result: FAILURE")

    return TestRunReport(
        codebase_version=codebase_version,
        commit_hash=commit_hash,
        baseline_signature=baseline_signature,
        environment_signature=environment_signature,
        configuration=config,
        report=report,
    )


def run_config(
    config_name: str,
    config_output: str,
    skip_validation: bool,
    exit_before_execution: bool,
    output_path_override: Optional[str],
):
    config_src = load_dict_with_references(config_name)

    if not skip_validation:
        logger.info("Validating configuration...")
        validation_errors = validate_config(config_src)
        if validation_errors:
            for e in validation_errors:
                logger.error("[{}]: {}", e.json_path, e.message)
            raise ValueError(
                f"{len(validation_errors)} validation errors indicated above.  Hint: resolve the clearest error first and then rerun validation."
            )

    whole_config = ImplicitDict.parse(config_src, USSQualifierConfiguration)

    if config_output:
        logger.info("Writing flattened configuration to {}", config_output)
        if config_output.lower().endswith(".json"):
            with open(config_output, "w") as f:
                json.dump(whole_config, f, indent=2, sort_keys=True)
        elif config_output.lower().endswith(".yaml"):
            with open(config_output, "w") as f:
                yaml.dump(json.loads(json.dumps(whole_config)), f, sort_keys=True)
        else:
            raise ValueError(
                "Unsupported extension for --config-output; only .json or .yaml file paths may be specified"
            )

    if exit_before_execution:
        logger.info("Exiting because --exit-before-execution specified.")
        return

    config: USSQualifierConfigurationV1 = whole_config.v1

    logger.info("Executing test run")
    report = execute_test_run(whole_config)

    if config.artifacts:
        generate_artifacts(report, config.artifacts, output_path_override)

    if "validation" in config and config.validation:
        logger.info(f"Validating test run report for configuration '{config_name}'")
        if not validate_report(report, config.validation):
            logger.error(
                f"Validation failed on test run report for configuration '{config_name}'"
            )
            return -1

    return os.EX_OK


def main() -> int:
    args = parseArgs()

    config_names = str(args.config).split(",")

    if args.config_output:
        config_outputs = str(args.config_output).split(",")
        if len(config_outputs) != len(config_names):
            raise ValueError(
                f"Need matching number of config_output, expected {len(config_names)}, got {len(config_outputs)}"
            )
    else:
        config_outputs = ["" for _ in config_names]

    for idx, config_name in enumerate(config_names):
        logger.info(
            f"========== Running uss_qualifier for configuration {config_name} =========="
        )
        exit_code = run_config(
            config_name,
            config_outputs[idx],
            args.skip_validation,
            args.exit_before_execution,
            args.output_path,
        )
        if exit_code != os.EX_OK:
            return exit_code
        logger.info(
            f"========== Completed uss_qualifier for configuration {config_name} =========="
        )

    return os.EX_OK


if __name__ == "__main__":
    sys.exit(main())
