#!env/bin/python3

import argparse
import json
import os
import sys

from implicitdict import ImplicitDict
from loguru import logger

from monitoring.monitorlib.dicts import remove_elements
from monitoring.monitorlib.versioning import get_code_version, get_commit_hash
from monitoring.uss_qualifier.configurations.configuration import (
    TestConfiguration,
    USSQualifierConfiguration,
    ArtifactsConfiguration,
    ReportConfiguration,
)
from monitoring.uss_qualifier.reports.documents import make_report_html
from monitoring.uss_qualifier.reports.tested_roles import generate_tested_roles
from monitoring.uss_qualifier.reports.graphs import make_graph
from monitoring.uss_qualifier.reports.report import TestRunReport, redact_access_tokens
from monitoring.uss_qualifier.resources.resource import create_resources
from monitoring.uss_qualifier.signatures import (
    compute_signature,
    compute_baseline_signature,
)
from monitoring.uss_qualifier.suites.suite import TestSuiteAction


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute USS Qualifier")

    parser.add_argument(
        "--config",
        help="Configuration string according to monitoring/uss_qualifier/configurations/README.md",
        required=True,
    )

    parser.add_argument(
        "--report",
        default=None,
        help="(Overrides setting in artifacts configuration) File name of the report to write (if test configuration provided) or read (if test configuration not provided)",
    )

    return parser.parse_args()


def execute_test_run(
    config: TestConfiguration, whole_config: USSQualifierConfiguration
):
    codebase_version = get_code_version()
    commit_hash = get_commit_hash()

    # Compute signatures of inputs
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

    resources = create_resources(config.resources.resource_declarations)
    action = TestSuiteAction(config.action, resources)
    report = action.run()
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


def main() -> int:
    args = parseArgs()

    whole_config = USSQualifierConfiguration.from_string(args.config)
    config = whole_config.v1
    if args.report:
        if not config.artifacts:
            config.artifacts = ArtifactsConfiguration(
                ReportConfiguration(report_path=args.report)
            )
        elif not config.artifacts.report:
            config.artifacts.report = ReportConfiguration(report_path=args.report)
        else:
            config.artifacts.report.report_path = args.report

    do_not_save_report = False
    if config.test_run:
        report = execute_test_run(config.test_run, whole_config)
    elif config.artifacts and config.artifacts.report:
        with open(config.artifacts.report.report_path, "r") as f:
            report = ImplicitDict.parse(json.load(f), TestRunReport)
            do_not_save_report = True  # No reason to re-save what we just loaded
    else:
        raise ValueError(
            "No input provided; test_run or artifacts.report.report_path must be specified in configuration"
        )

    if config.artifacts:
        if config.artifacts.report and not do_not_save_report:
            if config.artifacts.report.redact_access_tokens:
                logger.info("Redacting access tokens in report")
                redact_access_tokens(report)
            logger.info("Writing report to {}", config.artifacts.report.report_path)
            with open(config.artifacts.report.report_path, "w") as f:
                json.dump(report, f, indent=2)

        if config.artifacts.report_html:
            logger.info(
                "Writing HTML report to {}", config.artifacts.report_html.html_path
            )
            with open(config.artifacts.report_html.html_path, "w") as f:
                f.write(make_report_html(report))

        if config.artifacts.graph:
            logger.info(
                "Writing GraphViz dot source to {}", config.artifacts.graph.gv_path
            )
            with open(config.artifacts.graph.gv_path, "w") as f:
                f.write(make_graph(report).source)

        if config.artifacts.tested_roles:
            path = config.artifacts.tested_roles.report_path
            logger.info("Writing tested roles view to {}", path)
            generate_tested_roles(report, path)

    return os.EX_OK


if __name__ == "__main__":
    sys.exit(main())
