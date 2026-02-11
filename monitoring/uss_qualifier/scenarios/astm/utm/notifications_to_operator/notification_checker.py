from abc import ABC
from dataclasses import dataclass
from datetime import datetime, timedelta

import arrow
from uas_standards.astm.f3548.v21.constants import (
    ConflictingOIMaxUserNotificationTimeSeconds,
    TimeSyncMaxDifferentialSeconds,
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

NOTIFICATIONS_MAX_CLOCK_SKEW = timedelta(seconds=TimeSyncMaxDifferentialSeconds)
SCD0090_NOTE_PREFIX = "scd0090_notification"
SCD0095_NOTE_PREFIX = "scd0095_notification"
NOTIFICATION_NOTE_FORMAT = "{participant_id} notification latency: >{latency}s"
MAX_LATENCY = f"{ConflictingOIMaxUserNotificationTimeSeconds}"
_ACCEPTABLE_CONFLICTS = {Conflict.Single, Conflict.Multiple}


@dataclass
class Notifications:
    notifications: list[UserNotification] | None
    query: Query


class NotificationChecker(GenericTestScenario, ABC):
    """Helper class to do notification checks"""

    def _get_preexisting_notifications(
        self, clients: list[FlightPlannerClient]
    ) -> dict[ParticipantID, Notifications]:
        notifications = {}
        start_point = arrow.utcnow().datetime - NOTIFICATIONS_MAX_CLOCK_SKEW
        for client in clients:
            resp, query = client.get_user_notifications(after=start_point)
            self.record_query(query)
            with self.check(
                "Retrieve pre-existing notifications", client.participant_id
            ) as check:
                if not resp or "user_notifications" not in resp:
                    notifications[client.participant_id] = Notifications(
                        notifications=None, query=query
                    )
                    check.record_failed(
                        summary="No notifications returned",
                        details=f"{client.participant_id} didn't return a list of notifications when querying for pre-existing notifications",
                        query_timestamps=[query.request.timestamp],
                    )
                    continue

                if any(
                    [
                        notification.observed_at.datetime
                        > arrow.now() + NOTIFICATIONS_MAX_CLOCK_SKEW
                        for notification in resp.user_notifications
                    ]
                ):
                    notifications[client.participant_id] = Notifications(
                        notifications=None, query=query
                    )
                    check.record_failed(
                        summary="Error while trying to retrieve notifications",
                        details=f"Response from {client.participant_id} returned notifications in the future.",
                        query_timestamps=[query.request.timestamp],
                    )
                    continue

                notifications[client.participant_id] = Notifications(
                    notifications=resp.user_notifications, query=query
                )
        return notifications

    def _get_notifications(
        self,
        clients: list[FlightPlannerClient],
        start_point: datetime,
        deadline: datetime,
        preexisting_notifications: dict[ParticipantID, Notifications],
    ) -> dict[ParticipantID, Notifications]:
        start_point -= NOTIFICATIONS_MAX_CLOCK_SKEW
        notifications = {}
        most_recent_check = arrow.utcnow().datetime
        while most_recent_check < deadline:
            for client in clients:
                if client.participant_id in notifications:
                    # We've already found notifications for this participant
                    continue
                if (
                    client.participant_id not in preexisting_notifications
                    or preexisting_notifications[client.participant_id].notifications
                    is None
                ):
                    # We weren't able to retrieve the "before" notifications, so don't attempt to retrieve the "after" notifications
                    notifications[client.participant_id] = None
                    continue
                resp, query = client.get_user_notifications(after=start_point)
                self.record_query(query)
                most_recent_check = query.response.reported.datetime

                # See if we were able to retrieve notifications
                with self.check(
                    "Retrieve notifications", client.participant_id
                ) as check:
                    if not resp or "user_notifications" not in resp:
                        notifications[client.participant_id] = Notifications(
                            notifications=None, query=query
                        )
                        check.record_failed(
                            summary="No notifications returned",
                            details=f"{client.participant_id} didn't return a list of notifications when querying for new notifications",
                            query_timestamps=[query.request.timestamp],
                        )
                        continue

                    if any(
                        [
                            notification.observed_at.datetime
                            > arrow.now() + NOTIFICATIONS_MAX_CLOCK_SKEW
                            for notification in resp.user_notifications
                        ]
                    ):
                        notifications[client.participant_id] = Notifications(
                            notifications=None, query=query
                        )
                        check.record_failed(
                            summary="Error while trying to retrieve notifications",
                            details=f"Response from {client.participant_id} returned notifications in the future.",
                            query_timestamps=[query.request.timestamp],
                        )
                        continue

                # If there was at least one qualifying notification, use the response obtained for this participant
                previously_observed = {
                    n.observed_at
                    for n in preexisting_notifications[
                        client.participant_id
                    ].notifications
                    or []
                }
                qualifying_notifications = [
                    n
                    for n in resp.user_notifications
                    if n.conflicts in _ACCEPTABLE_CONFLICTS
                    and n.observed_at not in previously_observed
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

        return {k: v for k, v in notifications.items() if v is not None}

    def _check_for_user_notifications(
        self,
        causing_conflict: FlightPlannerClient,
        observing_conflict: FlightPlannerClient,
        preexisting_notifications: dict[ParticipantID, Notifications],
        earliest_action_time: datetime,
        latest_action_time: datetime,
    ):
        new_notifications = self._get_notifications(
            clients=[causing_conflict, observing_conflict],
            start_point=earliest_action_time,
            deadline=latest_action_time
            + timedelta(seconds=ConflictingOIMaxUserNotificationTimeSeconds),
            preexisting_notifications=preexisting_notifications,
        )

        def _latency_of(notifications: list[UserNotification]) -> str:
            if not notifications:
                return MAX_LATENCY
            dt = (
                max(notification.observed_at.datetime for notification in notifications)
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
                    new_notifications[client.participant_id].notifications or []
                ),
            )

        def _maybe_record_note(prefix: str, client: FlightPlannerClient) -> None:
            if (
                client.participant_id in new_notifications
                and new_notifications[client.participant_id].notifications is not None
            ):
                self.record_note(prefix, _note_for(client))

        _maybe_record_note(SCD0090_NOTE_PREFIX, causing_conflict)
        _maybe_record_note(SCD0095_NOTE_PREFIX, observing_conflict)
