from typing import Optional
from urllib.parse import urlparse

from implicitdict import ImplicitDict
from monitoring.monitorlib.clients.geospatial_info.client import GeospatialInfoClient
from monitoring.monitorlib.clients.geospatial_info.client_geospatial_map import (
    GeospatialMapClient,
)
from monitoring.monitorlib.infrastructure import AuthAdapter, UTMClientSession
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource
from monitoring.uss_qualifier.resources.resource import Resource
from uas_standards.interuss.automated_testing.geospatial_map.v1.constants import (
    Scope as ScopeGeospatialMap,
)


class GeospatialInfoProviderConfiguration(ImplicitDict):
    participant_id: str
    """ID of the geospatial information provider for which geospatial data can be queried"""

    geospatial_map_v1_base_url: Optional[str]
    """Base URL for the geospatial information provider's implementation of the interfaces/automated_testing/geospatial_map/v1/geospatial_map.yaml API"""

    timeout_seconds: Optional[float] = None
    """Number of seconds to allow for requests to this geospatial information provider.  If None, use default."""

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        if "geospatial_map_v1_base_url" in self and self.geospatial_map_v1_base_url:
            try:
                urlparse(self.geospatial_map_v1_base_url)
            except ValueError:
                raise ValueError(
                    "GeospatialInfoProviderConfiguration.geospatial_map_v1_base_url must be a URL"
                )

    def to_client(self, auth_adapter: AuthAdapter) -> GeospatialInfoClient:
        if "geospatial_map_v1_base_url" in self and self.geospatial_map_v1_base_url:
            session = UTMClientSession(
                self.geospatial_map_v1_base_url, auth_adapter, self.timeout_seconds
            )
            return GeospatialMapClient(session, self.participant_id)
        raise ValueError(
            "Could not construct GeospatialInfoClient from provided configuration"
        )


class GeospatialInfoProviderSpecification(ImplicitDict):
    geospatial_info_provider: GeospatialInfoProviderConfiguration


class GeospatialInfoProviderResource(Resource[GeospatialInfoProviderSpecification]):
    client: GeospatialInfoClient
    participant_id: ParticipantID

    def __init__(
        self,
        specification: GeospatialInfoProviderSpecification,
        auth_adapter: AuthAdapterResource,
    ):
        if (
            "geospatial_map_v1_base_url" in specification.geospatial_info_provider
            and specification.geospatial_info_provider.geospatial_map_v1_base_url
        ):
            auth_adapter.assert_scopes_available(
                scopes_required={
                    ScopeGeospatialMap.Query: "query geospatial map features from USSs under test",
                },
                consumer_name=f"{self.__class__.__name__} using geospatial_map v1 API",
            )
        else:
            raise NotImplementedError(
                "The means by which to interact with the geospatial information provider is not currently supported in GeospatialInfoProviderResource (geospatial_map_v1_base_url was not specified)"
            )

        self.client = specification.geospatial_info_provider.to_client(
            auth_adapter.adapter
        )
        self.participant_id = specification.geospatial_info_provider.participant_id
