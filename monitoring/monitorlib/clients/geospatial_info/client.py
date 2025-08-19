from abc import ABC, abstractmethod

from monitoring.monitorlib.clients.geospatial_info.querying import (
    GeospatialFeatureCheck,
    GeospatialFeatureQueryResponse,
)
from monitoring.monitorlib.fetch import QueryError
from monitoring.uss_qualifier.configurations.configuration import ParticipantID


class GeospatialInfoError(QueryError):
    pass


class GeospatialInfoClient(ABC):
    """Client to interact with a USS as a user/app asking for geospatial information and as the test director preparing for tests involving geospatial information."""

    participant_id: ParticipantID

    def __init__(self, participant_id: ParticipantID):
        self.participant_id = participant_id

    # ===== Emulation of user/app actions =====

    @abstractmethod
    def query_geospatial_features(
        self, checks: list[GeospatialFeatureCheck]
    ) -> GeospatialFeatureQueryResponse:
        """Instruct the USS to emulate a normal user/app trying to check for the specified geospatial information.

        Raises:
            * GeospatialInfoError
        """
        raise NotImplementedError()
