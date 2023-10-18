from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from monitoring.monitorlib.fetch import QueryError, Query
from monitoring.uss_qualifier.configurations.configuration import ParticipantID


class VersionQueryError(QueryError):
    pass


@dataclass
class GetVersionResponse(object):
    version: str
    query: Query


class VersioningClient(ABC):
    """Client to obtain version information from a USSs."""

    participant_id: ParticipantID

    def __init__(self, participant_id: ParticipantID):
        self.participant_id = participant_id

    @abstractmethod
    def get_version(self, version_type: Optional[str]) -> GetVersionResponse:
        """Retrieve the version of the specified system.

        Args:
            version_type: Identifier describing the system for which the version should be retrieved.

        Returns: Version of the specified system
        """
        raise NotImplementedError()
