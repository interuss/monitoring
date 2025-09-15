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


class NotificationChecker(GenericTestScenario, ABC):
    """Helper class to do notification checks"""

    def _record_current_notifications(self, uss: FlightPlannerClient):
        self._notifications_start_point = arrow.utcnow().datetime

        with self.check("Retrive notifications", [uss.participant_id]) as check:
            try:
                self._base_notifications_response, query = uss.get_user_notifications(
                    before=self._notifications_start_point
                    + timedelta(
                        seconds=ConflictingOIMaxUserNotificationTimeSeconds + 2
                    ),
                    after=self._notifications_start_point,
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
                    summary="Unable to retrive base notifications",
                    details=f"USS {uss.participant_id} didn't returned a list of notification before the action to compare as a base.",
                    query_timestamps=[query.request.timestamp] if query else [],
                )
                self._base_notifications_response = None

    def _wait_for_conflit_notification(self, uss: FlightPlannerClient):
        def _notification_filter(n):
            return "conflicts" not in n or n.conflicts in [
                Conflict.Unknown,
                Conflict.Single,
                Conflict.Multiple,
            ]

        with self.check(
            "New notification about conflict", [uss.participant_id]
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

            def _check():
                notifications, query = uss.get_user_notifications(
                    before=self._notifications_start_point
                    + timedelta(
                        seconds=ConflictingOIMaxUserNotificationTimeSeconds + 2
                    ),
                    after=self._notifications_start_point,
                )

                self.record_query(query)

                if not notifications or "user_notifications" not in notifications:
                    check.record_failed(
                        summary="No notification returned",
                        details=f"USS {uss.participant_id} didn't returned a list of notification when quering for new notifications.",
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
                seconds=ConflictingOIMaxUserNotificationTimeSeconds + 2
            )

            while arrow.utcnow() < deadline:
                if _check():
                    return

                time.sleep(0.2)

            if not _check():  # Do a final check after the wait
                # TODO: To test fully the requierements, we should record the
                # faillure and test in some aggregate analysis whether 95% of
                # these notifications were received within that threshold
                check.record_failed(
                    summary="No new notification about conflict recieved",
                    details=f"USS {uss.participant_id} didn't created a new notifications about conflict.",
                )
