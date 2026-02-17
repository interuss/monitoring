import datetime

import arrow
from implicitdict import ImplicitDict, StringBasedDateTime
from uas_standards.astm.f3411.v22a import constants
from uas_standards.interuss.automated_testing.rid.v1.injection import (
    Time,
    UserNotification,
)

from monitoring.monitorlib.rid_automated_testing import injection_api
from monitoring.monitorlib.rid_automated_testing.injection_api import (
    MANDATORY_POSITION_FIELDS,
    MANDATORY_TELEMETRY_FIELDS,
    TestFlight,
)

from . import database


class ServiceProviderUserNotifications(ImplicitDict):
    user_notifications: list[UserNotification] = []

    def record_notification(
        self,
        message: str | None = None,
        observed_at: datetime.datetime | None = None,
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

        for notif_date, notif_str in check_and_generate_missing_fields_notifications(
            record.flights
        ):
            self.record_notification(message=notif_str, observed_at=notif_date)


def check_and_generate_missing_fields_notifications(
    injected_flights: list[TestFlight],
) -> list[tuple[datetime.datetime, str]]:
    missing_fields_notifications = []

    for flight in injected_flights:
        # Default to now if we don't find anything
        default_timestamp = arrow.utcnow()

        # We try to use the start of the flight as a better default
        f_start, _ = flight.get_span()
        if f_start is None:  # get_span may fail to find a start
            default_timestamp = arrow.get(f_start)

        for tpos, telemetry in enumerate(flight.raw_telemetry):
            best_timestamp = telemetry.get(
                "timestamp", default_timestamp
            )  # We try to use the timestamp of the faulty telemetry

            # Update the default timestamp to the current one, so if the next
            # telemetry has no timestamp, we should be close with the previous
            # one
            default_timestamp = best_timestamp

            for mandatory_field in MANDATORY_TELEMETRY_FIELDS:
                if telemetry.get(mandatory_field, None) is None:
                    missing_fields_notifications.append(
                        (
                            best_timestamp.datetime,
                            f"Flight #{flight.injection_id}, Telemetry #{tpos}, missing field {mandatory_field}",
                        )
                    )

            if telemetry.get("position", None):
                for mandatory_field in MANDATORY_POSITION_FIELDS:
                    if telemetry["position"].get(mandatory_field, None) is None:
                        missing_fields_notifications.append(
                            (
                                best_timestamp.datetime,
                                f"Flight #{flight.injection_id}, Telemetry #{tpos}, missing field position.{mandatory_field}",
                            )
                        )

    return missing_fields_notifications


def check_and_generate_slow_update_notification(
    injected_flights: list[injection_api.TestFlight],
) -> list[datetime.datetime]:
    """
    Iterate over the provided list of injected TestFlight objects and, for any flight that has
    an average update rate under 1Hz, return a time for which a notification should be sent to the operator.
    """
    operator_slow_update_notifications: list[datetime.datetime] = []
    for f in injected_flights:
        # Mean rate is not technically correct as per Net0040
        # (20% of the samples may be above 1Hz with a mean rate below 1Hz),
        # but sufficient to trigger a notification to test the relevant scenario.

        f_start, _ = f.get_span()
        if not f_start:
            continue

        # Compute update rate in 1s buckets:
        rates = f.get_update_rates()

        if not rates:
            continue

        # Check in a moving window of 10s, that NetMinUasLocRefreshPercentage
        # samples are >= NetMinUasLocRefreshFrequency
        MOVING_WINDOW_DURATION: int = 10

        if len(rates) < MOVING_WINDOW_DURATION:
            continue

        for wpos in range(0, len(rates) - MOVING_WINDOW_DURATION):
            count_ok = sum(
                [
                    1 if rate >= constants.NetMinUasLocRefreshFrequencyHz else 0
                    for rate in rates[wpos : wpos + MOVING_WINDOW_DURATION]
                ]
            )

            if (
                count_ok
                < constants.NetMinUasLocRefreshPercentage
                / 100.0
                * MOVING_WINDOW_DURATION
            ):
                operator_slow_update_notifications.append(
                    f_start
                    + datetime.timedelta(
                        seconds=wpos + 2 + MOVING_WINDOW_DURATION
                    )  # get_update_rates is skipping the first 2 seconds (moving average of 3)
                )
    return operator_slow_update_notifications
