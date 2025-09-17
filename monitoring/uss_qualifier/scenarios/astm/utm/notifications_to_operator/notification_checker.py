from abc import ABC
from dataclasses import dataclass
from datetime import datetime, timedelta

import arrow
from uas_standards.astm.f3548.v21.constants import (
    ConflictingOIMaxUserNotificationTimeSeconds,
)

from monitoring.monitorlib.clients.flight_planning.client import (
    FlightPlannerClient,
)
from monitoring.monitorlib.clients.flight_planning.planning import (
    Conflict,
    UserNotification,
)
from monitoring.monitorlib.delay import sleep
from monitoring.monitorlib.fetch import Query
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario

NOTIFICATION_NOTE_FORMAT = "{participant_id} notification latency: >{latency}s"
MAX_LATENCY = f"{ConflictingOIMaxUserNotificationTimeSeconds}"
_ACCEPTABLE_CONFLICTS = {Conflict.Single, Conflict.Multiple}


@dataclass
class Notifications:
    notifications: list[UserNotification]
    query: Query


class NotificationChecker(GenericTestScenario, ABC):
    """Helper class to do notification checks"""

    def _get_notifications(
        self,
        clients: list[FlightPlannerClient],
        start_point: datetime,
        deadline: datetime,
    ) -> dict[ParticipantID, Notifications]:
        notifications = {}
        most_recent_check = arrow.utcnow().datetime
        while most_recent_check < deadline:
            for client in clients:
                if client.participant_id in notifications:
                    # We've already found notifications for this participant
                    continue
                resp, query = client.get_user_notifications(after=start_point)
                self.record_query(query)
                most_recent_check = query.response.reported.datetime

                # See if we were able to retrieve notifications
                with self.check(
                    "Retrieve notifications", client.participant_id
                ) as check:
                    if not resp or "user_notifications" not in resp:
                        print(resp)
                        notifications[client.participant_id] = Notifications(
                            notifications=[], query=query
                        )
                        check.record_failed(
                            summary="No notifications returned",
                            details=f"USS {client.participant_id} didn't return a list of notifications when querying for new notifications.",
                            query_timestamps=[query.request.timestamp],
                        )
                        continue

                # If there was at least one qualifying notification, use the response obtained for this participant
                qualifying_notifications = [
                    notification
                    for notification in resp.user_notifications
                    if notification.conflicts in _ACCEPTABLE_CONFLICTS
                ]
                if qualifying_notifications:
                    notifications[client.participant_id] = Notifications(
                        notifications=qualifying_notifications, query=query
                    )

            remaining_participants = [
                client.participant_id
                for client in clients
                if client.participant_id not in notifications
            ]
            if len(remaining_participants) > 0:
                sleep(
                    2,
                    f"user notifications have not yet appeared in {', '.join(remaining_participants)}",
                )
            else:
                break

        return notifications

    def _check_for_user_notifications(
        self,
        causing_conflict: FlightPlannerClient,
        observing_conflict: FlightPlannerClient,
        earliest_action_time: datetime,
        latest_action_time: datetime,
    ):
        new_notifications = self._get_notifications(
            [causing_conflict, observing_conflict],
            earliest_action_time,
            latest_action_time
            + timedelta(seconds=ConflictingOIMaxUserNotificationTimeSeconds),
        )

        def _latency_of(notifications: list[UserNotification]) -> str:
            if not notifications:
                return MAX_LATENCY
            else:
                dt = (
                    max(
                        notification.observed_at.datetime
                        for notification in notifications
                    )
                    - latest_action_time
                )
                if dt.total_seconds() > ConflictingOIMaxUserNotificationTimeSeconds:
                    return MAX_LATENCY
                elif dt.total_seconds() < 0:
                    return "0"
                else:
                    return f"{dt.total_seconds():.1f}"

        def _note_for(client: FlightPlannerClient) -> str:
            return NOTIFICATION_NOTE_FORMAT.format(
                participant_id=client.participant_id,
                latency=_latency_of(
                    new_notifications[client.participant_id].notifications
                ),
            )

        self.record_note(
            "scd0090_notification",
            _note_for(causing_conflict),
        )
        self.record_note("scd0095_notification", _note_for(observing_conflict))
