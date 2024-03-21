from datetime import datetime
from typing import List

from monitoring.monitorlib import schema_validation
from monitoring.uss_qualifier.scenarios.scenario import PendingCheck


def fail_with_schema_errors(
    check: PendingCheck,
    errors: List[schema_validation.ValidationError],
    t_dss: datetime,
) -> None:
    """
    Fail the passed check with the passed schema validation errors.
    """
    details = "\n".join(f"[{e.json_path}] {e.message}" for e in errors)
    check.record_failed(
        summary="Response format was invalid",
        details="Found the following schema validation errors in the DSS response:\n"
        + details,
        query_timestamps=[t_dss],
    )
