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

    tested_uss: FlightPlannerClient
    control_uss: FlightPlannerClient

    def _record_current_notifications(self):
        self._notifications_start_point = arrow.utcnow().datetime

        self._base_notifications_response = {}

        for participant in [self.tested_uss, self.control_uss]:
            with self.check(
                "Retrieve notifications", [participant.participant_id]
            ) as check:
                try:
                    (
                        self._base_notifications_response[participant.participant_id],
                        query,
                    ) = participant.get_user_notifications(
                        before=self._notifications_start_point
                        + timedelta(
                            seconds=ConflictingOIMaxUserNotificationTimeSeconds
                            + EXTRA_DELAY
                        ),
                        after=self._notifications_start_point,
                    )

                    self.record_query(query)

                except PlanningActivityError:
                    (
                        self._base_notifications_response[participant.participant_id],
                        query,
                    ) = (
                        None,
                        None,
                    )

                if (
                    not self._base_notifications_response[participant.participant_id]
                    or "user_notifications"
                    not in self._base_notifications_response[participant.participant_id]
                ):
                    check.record_failed(
                        summary="Unable to retrieve base notifications",
                        details=f"USS {participant.participant_id} didn't return a list of notifications before the action to compare as a base.",
                        query_timestamps=[query.request.timestamp] if query else [],
                    )
                    self._base_notifications_response[participant.participant_id] = None

    def _wait_for_conflict_notification(self):
        def _notification_filter(n):
            return "conflicts" not in n or n.conflicts in [
                Conflict.Unknown,
                Conflict.Single,
                Conflict.Multiple,
            ]

        def _generic_check(participant, check_name, count=1):
            with self.check(
                check_name,
                [participant.participant_id],
            ) as check:
                if not self._base_notifications_response[participant.participant_id]:
                    # No query: not supported API
                    check.skip()
                    return

                base_count = len(
                    list(
                        filter(
                            _notification_filter,
                            self._base_notifications_response[
                                participant.participant_id
                            ].user_notifications,
                        )
                    )
                )

                def _check_for_new_notifications():
                    notifications, query = participant.get_user_notifications(
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
                            details=f"USS {participant.participant_id} didn't return a list of notifications when querying for new notifications.",
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
                        >= base_count + count
                    )

                deadline = arrow.utcnow() + timedelta(
                    seconds=ConflictingOIMaxUserNotificationTimeSeconds + EXTRA_DELAY
                )

                while arrow.utcnow() < deadline:
                    if _check_for_new_notifications():
                        return

                    time.sleep(0.2)

                if (
                    not _check_for_new_notifications()
                ):  # Do a final check after the wait
                    # TODO: To test fully the requirements, we should record the
                    # failure and test in some aggregated analysis whether 95% of
                    # these notifications were received within that threshold
                    check.record_failed(
                        summary="No new notification about conflict received",
                        details=f"USS {participant.participant_id} didn't create a new notifications about conflict.",
                    )

        _generic_check(
            self.control_uss, "New notification about conflict on creation/modification"
        )

        # if control_uss and tested_uss USS are the same, we do expect 2
        # notification, since one has already been 'consumed' for
        # creation/modification
        # We don't have much data on notification, so we don't know witch one
        # is for creation and witch one is for awareness.
        # We could also set both check to two, but that allow to differentiate
        # the case where only one notification is send (that will be
        # prioritized for creation/modification arbitrarily).
        _generic_check(
            self.tested_uss,
            "New notification about conflict on awareness",
            2 if self.control_uss == self.tested_uss else 1,
        )
