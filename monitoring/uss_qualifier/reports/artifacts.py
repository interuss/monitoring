import json
import os
import time
from multiprocessing import Process

from implicitdict import ImplicitDict
from loguru import logger

from monitoring.uss_qualifier.configurations.configuration import ArtifactsConfiguration
from monitoring.uss_qualifier.reports.documents import make_report_html
from monitoring.uss_qualifier.reports.globally_expanded.generate import (
    generate_globally_expanded_report,
)
from monitoring.uss_qualifier.reports.report import TestRunReport, redact_access_tokens
from monitoring.uss_qualifier.reports.sequence_view.generate import (
    generate_sequence_view,
)
from monitoring.uss_qualifier.reports.templates import render_templates
from monitoring.uss_qualifier.reports.tested_requirements.generate import (
    generate_tested_requirements,
)
from monitoring.uss_qualifier.reports.timing.generate import generate_timing_report


def default_output_path(config_name: str) -> str:
    if config_name.lower().endswith(".yaml") or config_name.lower().endswith(".json"):
        simple_config_name = os.path.splitext(config_name)[0]
    else:
        simple_config_name = config_name
    simple_config_name = simple_config_name.split(".")[-1]
    simple_config_name = os.path.split(simple_config_name)[-1]
    return os.path.join("output", simple_config_name)


def generate_artifacts(
    report: TestRunReport,
    artifacts: ArtifactsConfiguration,
    output_path: str,
    disallow_unredacted: bool,
):
    logger.debug(f"Writing artifacts to {os.path.abspath(output_path)}")
    try:
        os.makedirs(output_path, exist_ok=True)
    except PermissionError:
        pass  # This may be ok if writing directly to a single specific output folder provided to a container

    def _should_redact(cfg) -> bool:
        result = "redact_access_tokens" in cfg and cfg.redact_access_tokens
        if disallow_unredacted and not result:
            raise RuntimeError(
                "The option to disallow unredacted information was set, but the configuration specified unredacted information any way"
            )
        return result

    logger.info("Redacting access tokens from report")
    redacted_report = ImplicitDict.parse(json.loads(json.dumps(report)), TestRunReport)
    redact_access_tokens(redacted_report)

    def make_raw_report() -> None:
        if not artifacts.raw_report:
            return
        path = os.path.join(output_path, "report.json")
        logger.info(f"Writing raw report to {path}")
        t0 = time.monotonic()
        raw_report = artifacts.raw_report
        report_to_write = redacted_report if _should_redact(raw_report) else report
        with open(path, "w") as f:
            if "indent" in raw_report and raw_report.indent is not None:
                json.dump(report_to_write, f, indent=raw_report.indent)
            else:
                json.dump(report_to_write, f)
        logger.info(f"Wrote raw report in {time.monotonic() - t0:.1f}s")

    def make_html_report() -> None:
        if not artifacts.report_html:
            return
        path = os.path.join(output_path, "report.html")
        logger.info(f"Writing HTML report to {path}")
        t0 = time.monotonic()
        report_to_write = (
            redacted_report if _should_redact(artifacts.report_html) else report
        )
        with open(path, "w") as f:
            f.write(make_report_html(report_to_write))
        logger.info(f"Wrote HTML report in {time.monotonic() - t0:.1f}s")

    def make_templated_reports() -> None:
        if not artifacts.templated_reports:
            return
        render_templates(
            output_path,
            artifacts.templated_reports,
            redacted_report,
        )

    def make_tested_requirements() -> None:
        if not artifacts.tested_requirements:
            return
        for tested_reqs_config in artifacts.tested_requirements:
            path = os.path.join(output_path, tested_reqs_config.report_name)
            logger.info(f"Writing tested requirements view to {path}")
            t0 = time.monotonic()
            generate_tested_requirements(redacted_report, tested_reqs_config, path)
            logger.info(
                f"Wrote tested requirements view in {time.monotonic() - t0:.1f}s"
            )

    def make_sequence_view() -> None:
        if not artifacts.sequence_view:
            return
        path = os.path.join(output_path, "sequence")
        logger.info(f"Writing sequence view to {path}")
        t0 = time.monotonic()
        report_to_write = (
            redacted_report if _should_redact(artifacts.sequence_view) else report
        )
        generate_sequence_view(report_to_write, artifacts.sequence_view, path)
        logger.info(f"Wrote sequence view in {time.monotonic() - t0:.1f}s")

    def make_globally_expanded_report() -> None:
        if artifacts.globally_expanded_report is None:
            return
        path = os.path.join(output_path, "globally_expanded")
        logger.info(f"Writing globally-expanded report to {path}")
        t0 = time.monotonic()
        report_to_write = (
            redacted_report
            if _should_redact(artifacts.globally_expanded_report)
            else report
        )
        generate_globally_expanded_report(
            report_to_write, artifacts.globally_expanded_report, path
        )
        logger.info(f"Wrote globally-expanded report in {time.monotonic() - t0:.1f}s")

    def make_timing_report() -> None:
        if artifacts.timing_report is None:
            return
        path = os.path.join(output_path, "timing")
        logger.info(f"Writing timing report to {path}")
        t0 = time.monotonic()
        generate_timing_report(redacted_report, artifacts.timing_report, path)
        logger.info(f"Wrote timing report in {time.monotonic() - t0:.1f}s")

    artifact_generators = [
        make_raw_report,
        make_html_report,
        make_templated_reports,
        make_tested_requirements,
        make_sequence_view,
        make_globally_expanded_report,
        make_timing_report,
    ]
    generators = [Process(target=g, daemon=True) for g in artifact_generators]
    for p in generators:
        p.start()
    for p in generators:
        p.join()

    failed = [p for p in generators if p.exitcode != 0]
    if failed:
        raise RuntimeError(f"{len(failed)} generator(s) failed. Check exception above.")
