import json
import os
from typing import Optional

from loguru import logger

from implicitdict import ImplicitDict
from monitoring.uss_qualifier.configurations.configuration import ArtifactsConfiguration
from monitoring.uss_qualifier.reports.documents import make_report_html
from monitoring.uss_qualifier.reports.report import TestRunReport, redact_access_tokens
from monitoring.uss_qualifier.reports.sequence_view import generate_sequence_view
from monitoring.uss_qualifier.reports.templates import render_templates
from monitoring.uss_qualifier.reports.tested_requirements import (
    generate_tested_requirements,
)


def generate_artifacts(
    report: TestRunReport,
    artifacts: ArtifactsConfiguration,
    output_path_override: Optional[str] = None,
):
    output_path = output_path_override or artifacts.output_path
    os.makedirs(output_path, exist_ok=True)

    def _should_redact(cfg) -> bool:
        return "redact_access_tokens" in cfg and cfg.redact_access_tokens

    logger.info(f"Redacting access tokens from report")
    redacted_report = ImplicitDict.parse(json.loads(json.dumps(report)), TestRunReport)
    redact_access_tokens(redacted_report)

    if artifacts.raw_report:
        # Raw report
        path = os.path.join(output_path, "report.json")
        logger.info(f"Writing raw report to {path}")
        raw_report = artifacts.raw_report
        report_to_write = redacted_report if _should_redact(raw_report) else report
        with open(path, "w") as f:
            if "indent" in raw_report and raw_report.indent is not None:
                json.dump(report_to_write, f, indent=raw_report.indent)
            else:
                json.dump(report_to_write, f)

    if artifacts.report_html:
        # HTML rendering of raw report
        path = os.path.join(output_path, "report.html")
        logger.info(f"Writing HTML report to {path}")
        report_to_write = (
            redacted_report if _should_redact(artifacts.report_html) else report
        )
        with open(path, "w") as f:
            f.write(make_report_html(report_to_write))

    if artifacts.templated_reports:
        # Templated reports
        render_templates(
            output_path,
            artifacts.templated_reports,
            redacted_report,
        )

    if artifacts.tested_requirements:
        # Tested requirements view
        for tested_reqs_config in artifacts.tested_requirements:
            path = os.path.join(output_path, tested_reqs_config.report_name)
            logger.info(f"Writing tested requirements view to {path}")
            generate_tested_requirements(redacted_report, tested_reqs_config, path)

    if artifacts.sequence_view:
        # Sequence view
        path = os.path.join(output_path, "sequence")
        logger.info(f"Writing sequence view to {path}")
        report_to_write = (
            redacted_report if _should_redact(artifacts.sequence_view) else report
        )
        generate_sequence_view(report_to_write, artifacts.sequence_view, path)
