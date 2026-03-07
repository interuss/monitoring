from datetime import timedelta
from urllib.parse import urlparse

from uas_standards.astm.f3548.v21.api import (
    OperationalIntentDetails,
    OperationalIntentReference,
    UssAvailabilityState,
    Volume4D,
)

from monitoring.monitorlib.geotemporal import Volume4DCollection
from monitoring.monitorlib.scd import priority_of

NUMERIC_PRECISION = 0.001


def validate_op_intent_reference(
    uss_oi: OperationalIntentReference,
    dss_oi: OperationalIntentReference,
) -> str | None:
    # this function assumes all fields required by the OpenAPI definition are present as the format validation
    # should have been performed by OpIntentValidator._evaluate_op_intent_validation before
    errors_text: list[str] = []

    def append_err(name: str, uss_value: str, dss_value: str):
        errors_text.append(
            f"{name} reported by USS ({uss_value}) does not match the one published to the DSS ({dss_value})"
        )
        return

    if uss_oi.version != dss_oi.version:
        append_err("Version", str(uss_oi.version), str(dss_oi.version))

    # use str.lower() to tolerate case mismatch for string values
    if uss_oi.id.lower() != dss_oi.id.lower():
        append_err("ID", uss_oi.id, dss_oi.id)
    if uss_oi.manager.lower() != dss_oi.manager.lower():
        append_err("Manager", uss_oi.manager, dss_oi.manager)
    if uss_oi.state.lower() != dss_oi.state.lower():
        append_err("State", uss_oi.state, dss_oi.state)
    if uss_oi.subscription_id.lower() != dss_oi.subscription_id.lower():
        append_err("Subscription ID", uss_oi.subscription_id, dss_oi.subscription_id)
    if uss_oi.uss_availability.lower() != dss_oi.uss_availability.lower():
        # tolerate empty value if unknown
        if (
            len(uss_oi.uss_availability) != 0
            or dss_oi.uss_availability != UssAvailabilityState.Unknown
        ):
            append_err(
                "USS availability", uss_oi.uss_availability, dss_oi.uss_availability
            )

    if uss_oi.uss_base_url != dss_oi.uss_base_url:
        # tolerate differences in URL that have no impact
        uss_url = urlparse(uss_oi.uss_base_url)
        dss_url = urlparse(dss_oi.uss_base_url)
        if (
            uss_url.scheme != dss_url.scheme
            or uss_url.netloc != dss_url.netloc
            or uss_url.path != dss_url.path
        ):
            append_err("USS base URL", uss_oi.uss_base_url, dss_oi.uss_base_url)

    # tolerate USS starting later than published on DSS
    if uss_oi.time_start.value.datetime < dss_oi.time_start.value.datetime - timedelta(
        seconds=NUMERIC_PRECISION
    ):
        append_err("Start time", uss_oi.time_start.value, dss_oi.time_start.value)

    # tolerate USS ending sooner than published on DSS
    if uss_oi.time_end.value.datetime > dss_oi.time_end.value.datetime + timedelta(
        seconds=NUMERIC_PRECISION
    ):
        append_err("End time", uss_oi.time_start.value, dss_oi.time_start.value)

    return "; ".join(errors_text) if errors_text else None


def validate_op_intent_details(
    op_intent_details: OperationalIntentDetails,
    expected_priority: int,
    expected_extent: Volume4D,
) -> str | None:
    errors_text: list[str] = []

    # Check that the USS is providing matching priority
    actual_priority = priority_of(op_intent_details)
    if actual_priority != expected_priority:
        errors_text.append(
            f"Priority specified by USS in operational intent details ({actual_priority}) is different than the priority in the injected flight ({expected_priority})"
        )

    # Check that the USS is providing reasonable volume 4D
    resp_vol4s = op_intent_details.volumes + op_intent_details.off_nominal_volumes
    if len(resp_vol4s) == 0:
        errors_text.append(
            "OperationalIntentResponse did not return required volumes or off nominal volumes."
        )
        return "; ".join(errors_text) if len(errors_text) > 0 else None

    vol4c = Volume4DCollection.from_f3548v21(resp_vol4s)
    resp_alts = vol4c.meter_altitude_bounds
    resp_start = vol4c.time_start.datetime
    resp_end = vol4c.time_end.datetime
    if resp_alts[0] > expected_extent.volume.altitude_lower.value + NUMERIC_PRECISION:
        errors_text.append(
            f"Lower altitude specified by USS in operational intent details ({resp_alts[0]} m WGS84) is above the lower altitude in the injected flight ({expected_extent.volume.altitude_lower.value} m WGS84)"
        )
    elif resp_alts[1] < expected_extent.volume.altitude_upper.value - NUMERIC_PRECISION:
        errors_text.append(
            f"Upper altitude specified by USS in operational intent details ({resp_alts[1]} m WGS84) is below the upper altitude in the injected flight ({expected_extent.volume.altitude_upper.value} m WGS84)"
        )
    elif resp_start > expected_extent.time_start.value.datetime + timedelta(
        seconds=NUMERIC_PRECISION
    ):
        errors_text.append(
            f"Start time specified by USS in operational intent details ({resp_start.isoformat()}) is past the start time of the injected flight ({expected_extent.time_start.value})"
        )
    elif resp_end < expected_extent.time_end.value.datetime - timedelta(
        seconds=NUMERIC_PRECISION
    ):
        errors_text.append(
            f"End time specified by USS in operational intent details ({resp_end.isoformat()}) is prior to the end time of the injected flight ({expected_extent.time_end.value})"
        )

    return "; ".join(errors_text) if len(errors_text) > 0 else None
