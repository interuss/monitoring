import json
import os

from loguru import logger

from monitoring.benchmarker.configurations.artifacts.raw_report import (
    RawReportSpecification,
)
from monitoring.benchmarker.reports.report import BenchmarkRunReport


def generate_raw_report(
    report: BenchmarkRunReport, raw_spec: RawReportSpecification, output_dir: str
) -> None:
    filename = (
        raw_spec.name
        if raw_spec.name.lower().endswith(".json")
        else f"{raw_spec.name}.json"
    )
    out_path = os.path.join(output_dir, filename)
    logger.info(f"Writing raw report artifact to {out_path}")
    with open(out_path, "w") as f:
        json.dump(report, f, sort_keys=True)
