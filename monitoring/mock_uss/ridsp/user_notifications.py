from typing import Optional

import datetime
import arrow
from enum import Enum
from implicitdict import ImplicitDict, StringBasedDateTime

from uas_standards.interuss.automated_testing.rid.v1.injection import (
    UserNotification,
    Time,
)


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
