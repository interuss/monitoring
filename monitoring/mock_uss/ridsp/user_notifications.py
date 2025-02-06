from typing import Optional, List

import datetime
import arrow
from enum import Enum
from implicitdict import ImplicitDict, StringBasedDateTime

from uas_standards.interuss.automated_testing.rid.v1.injection import (
    UserNotification,
    Time,
)
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
