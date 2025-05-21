from abc import ABC, abstractmethod
from typing import List

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
        self, checks: List[GeospatialFeatureCheck]
    ) -> GeospatialFeatureQueryResponse:
        """Instruct the USS to emulate a normal user/app trying to check for the specified geospatial information.

        Raises:
            * GeospatialInfoError
        """
        raise NotImplementedError()

    @abstractmethod
    def get_dynamic_features(
        self, source_url: str, params: Optional[dict] = None
    ) -> dict:
        """
        Fetches features from a dynamic GeoJSON source.
        `params` could include interpretation_rule, etc.
        Returns a GeoJSON FeatureCollection as a dictionary.

        Raises:
            * GeospatialInfoError
        """
        raise NotImplementedError()

    @abstractmethod
    def get_dynamic_test_points(
        self, source_url: str, params: Optional[dict] = None
    ) -> List["LatLng"]:
        """
        Fetches features from a dynamic GeoJSON source and computes their centroids.
        `params` could include interpretation_rule, etc.
        Returns a list of s2sphere.LatLng points (centroids).

        Raises:
            * GeospatialInfoError
        """
        raise NotImplementedError()
