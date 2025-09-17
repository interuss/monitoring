from enum import Enum

from implicitdict import ImplicitDict, StringBasedDateTime

from monitoring.monitorlib.clients.flight_planning.planning import Conflict


class UserNotificationType(str, Enum):
    """Type of notification the virtual user received"""

    CausedConflict = "CausedConflict"
    """User's flight caused or has a conflict with another flight"""

    DetectedConflict = "DetectedConflict"
    """Another flight created a conflict with one of the user's flights"""


class UserNotification(ImplicitDict):
    type: UserNotificationType
    observed_at: StringBasedDateTime
    conflicts: Conflict
