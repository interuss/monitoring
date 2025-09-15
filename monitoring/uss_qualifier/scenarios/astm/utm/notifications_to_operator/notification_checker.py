import time
from abc import ABC
from datetime import timedelta

import arrow
from uas_standards.astm.f3548.v21.constants import (
    ConflictingOIMaxUserNotificationTimeSeconds,
)

from monitoring.monitorlib.clients.flight_planning.client import (
    FlightPlannerClient,
    PlanningActivityError,
)
from monitoring.monitorlib.clients.flight_planning.planning import (
    Conflict,
)
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario

# We add an (arbitrary) delay of 2 seconds, to allow some notifications to
# arrive later, staying in the 95% stated in the standard, until the TODO below
# in implemented.
EXTRA_DELAY = 2


class NotificationChecker(GenericTestScenario, ABC):
    """Helper class to do notification checks"""

    control_uss: FlightPlannerClient

    def _record_current_notifications(self):
        self._notifications_start_point = arrow.utcnow().datetime

        with self.check(
            "Retrieve notifications", [self.control_uss.participant_id]
        ) as check:
            try:
                self._base_notifications_response, query = (
                    self.control_uss.get_user_notifications(
                        before=self._notifications_start_point
                        + timedelta(
                            seconds=ConflictingOIMaxUserNotificationTimeSeconds
                            + EXTRA_DELAY
                        ),
                        after=self._notifications_start_point,
                    )
                )

                self.record_query(query)

            except PlanningActivityError:
                self._base_notifications_response, query = (
                    None,
                    None,
                )

            if (
                not self._base_notifications_response
                or "user_notifications" not in self._base_notifications_response
            ):
                check.record_failed(
                    summary="Unable to retrieve base notifications",
                    details=f"USS {self.control_uss.participant_id} didn't return a list of notifications before the action to compare as a base.",
                    query_timestamps=[query.request.timestamp] if query else [],
                )
                self._base_notifications_response = None

    def _wait_for_conflict_notification(self):
        def _notification_filter(n):
            return "conflicts" not in n or n.conflicts in [
                Conflict.Unknown,
                Conflict.Single,
                Conflict.Multiple,
            ]

        with self.check(
            "New notification about conflict", [self.control_uss.participant_id]
        ) as check:
            if not self._base_notifications_response:
                # No query: not supported API
                check.skip()
                return

            base_count = len(
                list(
                    filter(
                        _notification_filter,
                        self._base_notifications_response.user_notifications,
                    )
                )
            )

            def _check_for_new_notifications():
                notifications, query = self.control_uss.get_user_notifications(
                    before=self._notifications_start_point
                    + timedelta(
                        seconds=ConflictingOIMaxUserNotificationTimeSeconds
                        + EXTRA_DELAY
                    ),
                    after=self._notifications_start_point,
                )

                self.record_query(query)

                if not notifications or "user_notifications" not in notifications:
                    check.record_failed(
                        summary="No notification returned",
                        details=f"USS {self.control_uss.participant_id} didn't return a list of notifications when querying for new notifications.",
                        query_timestamps=[query.request.timestamp],
                    )
                    return

                return (
                    len(
                        list(
                            filter(
                                _notification_filter,
                                notifications.user_notifications,
                            )
                        )
                    )
                    > base_count
                )

            deadline = arrow.utcnow() + timedelta(
                seconds=ConflictingOIMaxUserNotificationTimeSeconds + EXTRA_DELAY
            )

            while arrow.utcnow() < deadline:
                if _check_for_new_notifications():
                    return

                time.sleep(0.2)

            if not _check_for_new_notifications():  # Do a final check after the wait
                # TODO: To test fully the requirements, we should record the
                # failure and test in some aggregated analysis whether 95% of
                # these notifications were received within that threshold
                check.record_failed(
                    summary="No new notification about conflict received",
                    details=f"USS {self.control_uss.participant_id} didn't create a new notifications about conflict.",
                )
