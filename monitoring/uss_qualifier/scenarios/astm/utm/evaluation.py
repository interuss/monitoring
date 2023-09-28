from datetime import timedelta
from typing import Optional, List

from monitoring.monitorlib.geotemporal import Volume4DCollection
from uas_standards.astm.f3548.v21.api import OperationalIntentDetails, Volume4D


NUMERIC_PRECISION = 0.001


def validate_op_intent_details(
    op_intent_details: OperationalIntentDetails,
    expected_priority: int,
    expected_extent: Volume4D,
) -> Optional[str]:
    errors_text: List[str] = []

    # Check that the USS is providing matching priority
    if op_intent_details.priority != expected_priority:
        errors_text.append(
            "Priority specified by USS in operational intent details ({}) is different than the priority in the injected flight ({})".format(
                op_intent_details.priority, expected_priority
            )
        )

    # Check that the USS is providing reasonable volume 4D
    resp_vol4s = op_intent_details.volumes + op_intent_details.off_nominal_volumes
    vol4c = Volume4DCollection.from_f3548v21(resp_vol4s)
    resp_alts = vol4c.meter_altitude_bounds
    resp_start = vol4c.time_start.datetime
    resp_end = vol4c.time_end.datetime
    if resp_alts[0] > expected_extent.volume.altitude_lower.value + NUMERIC_PRECISION:
        errors_text.append(
            "Lower altitude specified by USS in operational intent details ({} m WGS84) is above the lower altitude in the injected flight ({} m WGS84)".format(
                resp_alts[0], expected_extent.volume.altitude_lower.value
            )
        )
    elif resp_alts[1] < expected_extent.volume.altitude_upper.value - NUMERIC_PRECISION:
        errors_text.append(
            "Upper altitude specified by USS in operational intent details ({} m WGS84) is below the upper altitude in the injected flight ({} m WGS84)".format(
                resp_alts[1], expected_extent.volume.altitude_upper.value
            )
        )
    elif resp_start > expected_extent.time_start.value.datetime + timedelta(
        seconds=NUMERIC_PRECISION
    ):
        errors_text.append(
            "Start time specified by USS in operational intent details ({}) is past the start time of the injected flight ({})".format(
                resp_start.isoformat(), expected_extent.time_start.value
            )
        )
    elif resp_end < expected_extent.time_end.value.datetime - timedelta(
        seconds=NUMERIC_PRECISION
    ):
        errors_text.append(
            "End time specified by USS in operational intent details ({}) is prior to the end time of the injected flight ({})".format(
                resp_end.isoformat(), expected_extent.time_end.value
            )
        )

    return "; ".join(errors_text) if len(errors_text) > 0 else None
