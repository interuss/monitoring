import datetime
from typing import Optional, List

import arrow
from implicitdict import ImplicitDict, StringBasedDateTime
from uas_standards.interuss.automated_testing.rid.v1.injection import (
    UserNotification,
    Time,
)

from monitoring.monitorlib.rid_automated_testing import injection_api
from monitoring.monitorlib.rid_automated_testing.injection_api import TestFlight
from . import database


class ServiceProviderUserNotifications(ImplicitDict):
    user_notifications: list[UserNotification] = []

    def record_notification(
        self,
        message: Optional[str] = None,
        observed_at: Optional[datetime.datetime] = None,
    ):
        if not observed_at:
            observed_at = arrow.utcnow().datetime

        observed_at_time = Time(
            value=StringBasedDateTime(observed_at),
        )

        self.user_notifications.append(
            UserNotification(observed_at=observed_at_time, message=message)
        )

    def create_notifications_if_needed(self, record: "database.TestRecord"):
        for notif in check_and_generate_slow_update_notification(record.flights):
            self.record_notification("Insufficient update rate", notif)

        for notif in check_and_generate_missing_fields_notifications(record.flights):
            self.record_notification(notif)


def check_and_generate_missing_fields_notifications(
    injected_flights: List[TestFlight],
) -> List[str]:
    missing_fields_notifications = []

    for flight in injected_flights:
        for tpos, telemetry in enumerate(flight.raw_telemetry):
            for mandatory_field in flight.MANDATORY_TELEMETRY_FIELDS:
                if telemetry.get(mandatory_field, None) is None:
                    missing_fields_notifications.append(
                        f"Flight #{flight.injection_id}, Telemetry #{tpos}, missing field {mandatory_field}"
                    )

            if telemetry.get("position", None):
                for mandatory_field in flight.MANDATORY_POSITION_FIELDS:
                    if telemetry["position"].get(mandatory_field, None) is None:
                        missing_fields_notifications.append(
                            f"Flight #{flight.injection_id}, Telemetry #{tpos}, missing field position.{mandatory_field}"
                        )

    return missing_fields_notifications


def check_and_generate_slow_update_notification(
    injected_flights: List[injection_api.TestFlight],
) -> List[datetime]:
    """
    Iterate over the provided list of injected TestFlight objects and, for any flight that has
    an average update rate under 1Hz, return a time for which a notification should be sent to the operator.
    """
    operator_slow_update_notifications: List[datetime] = []
    for f in injected_flights:
        # Mean rate is not technically correct as per Net0040
        # (20% of the samples may be above 1Hz with a mean rate below 1Hz),
        # but sufficient to trigger a notification to test the relevant scenario.
        mean_rate = f.get_mean_update_rate_hz()
        if mean_rate and mean_rate < 0.99:
            # Arbitrarily use middle of the flight as notification time:
            f_start, f_end = f.get_span()
            if f_start and f_end:
                operator_slow_update_notifications.append(
                    f_start + (f_end - f_start) / 2
                )
    return operator_slow_update_notifications
