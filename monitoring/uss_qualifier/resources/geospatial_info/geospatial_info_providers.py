from typing import Optional
from urllib.parse import urlparse

from implicitdict import ImplicitDict
from uas_standards.interuss.automated_testing.geospatial_map.v1.constants import (
    Scope as ScopeGeospatialMap,
)

from monitoring.monitorlib.clients.geospatial_info.client import GeospatialInfoClient
from monitoring.monitorlib.clients.geospatial_info.client_geospatial_map import (
    GeospatialMapClient,
)
from monitoring.monitorlib.infrastructure import AuthAdapter, UTMClientSession
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource
from monitoring.uss_qualifier.resources.resource import Resource


class GeospatialInfoProviderConfiguration(ImplicitDict):
    participant_id: str
    """ID of the geospatial information provider for which geospatial data can be queried"""

    geospatial_map_v1_base_url: Optional[str]
    """Base URL for the geospatial information provider's implementation of the interfaces/automated_testing/geospatial_map/v1/geospatial_map.yaml API"""

    dynamic_source_url: Optional[str] = None
    """URL for the dynamic GeoJSON feed."""

    dynamic_source_type: Optional[str] = None
    """Type of the dynamic source (e.g., "geojson")."""

    dynamic_source_interpretation_rule: Optional[str] = None
    """Rule for interpreting features (e.g., "treat_all_as_restrictions")."""

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
        if "dynamic_source_url" in self and self.dynamic_source_url:
            try:
                urlparse(self.dynamic_source_url)
            except ValueError:
                raise ValueError(
                    "GeospatialInfoProviderConfiguration.dynamic_source_url must be a URL"
                )

    def to_client(self, auth_adapter: AuthAdapter) -> GeospatialInfoClient:
        if "geospatial_map_v1_base_url" in self and self.geospatial_map_v1_base_url:
            session = UTMClientSession(
                self.geospatial_map_v1_base_url, auth_adapter, self.timeout_seconds
            )
            return GeospatialMapClient(
                session,
                self.participant_id,
                dynamic_source_url=self.dynamic_source_url,
                dynamic_source_type=self.dynamic_source_type,
                dynamic_source_interpretation_rule=self.dynamic_source_interpretation_rule,
            )
        elif "dynamic_source_url" in self and self.dynamic_source_url:
            # For dynamic sources, we might not need a pre-configured session if it's a public URL
            # However, GeospatialMapClient expects a session. We can create a dummy session or adjust client.
            # For now, let's assume dynamic sources also use a session, potentially for auth in future.
            # If dynamic_source_url is public, auth_adapter might not be strictly needed for this specific client path,
            # but the structure expects it.
            session = UTMClientSession(
                # dynamic_source_url might not be a base URL for a session in the same way geospatial_map_v1_base_url is.
                # This might need refinement based on how GeospatialMapClient uses the session for dynamic sources.
                # For now, let's use a placeholder or the dynamic_source_url itself, assuming it might be a base for potential API calls.
                # A more robust solution might involve a different client or a sessionless path in GeospatialMapClient.
                base_url=self.dynamic_source_url,  # This might need adjustment
                auth_adapter=auth_adapter,
                timeout_sec=self.timeout_seconds,
            )
            return GeospatialMapClient(
                session,
                self.participant_id,
                dynamic_source_url=self.dynamic_source_url,
                dynamic_source_type=self.dynamic_source_type,
                dynamic_source_interpretation_rule=self.dynamic_source_interpretation_rule,
            )
        raise ValueError(
            "Could not construct GeospatialInfoClient from provided configuration: neither geospatial_map_v1_base_url nor dynamic_source_url was provided"
        )


class GeospatialInfoProviderSpecification(ImplicitDict):
    geospatial_info_provider: GeospatialInfoProviderConfiguration


class GeospatialInfoProviderResource(Resource[GeospatialInfoProviderSpecification]):
    client: GeospatialInfoClient
    participant_id: ParticipantID

    def __init__(
        self,
        specification: GeospatialInfoProviderSpecification,
        resource_origin: str,
        auth_adapter: AuthAdapterResource,
    ):
        super(GeospatialInfoProviderResource, self).__init__(
            specification, resource_origin
        )
        # Check if either static or dynamic configuration is present
        static_config_present = (
            "geospatial_map_v1_base_url" in specification.geospatial_info_provider
            and specification.geospatial_info_provider.geospatial_map_v1_base_url
        )
        dynamic_config_present = (
            "dynamic_source_url" in specification.geospatial_info_provider
            and specification.geospatial_info_provider.dynamic_source_url
        )

        if static_config_present:
            auth_adapter.assert_scopes_available(
                scopes_required={
                    ScopeGeospatialMap.Query: "query geospatial map features from USSs under test",
                },
                consumer_name=f"{self.__class__.__name__} using geospatial_map v1 API",
            )
        elif dynamic_config_present:
            # For dynamic sources, especially public URLs, auth might not be strictly necessary.
            # However, if the dynamic source URL were to require auth, different scopes might be needed.
            # For now, we'll assume no additional scopes are needed for public dynamic sources.
            # If specific scopes were required for dynamic sources, they would be asserted here.
            pass  # No specific scope assertion for public dynamic sources yet
        else:
            raise ValueError(
                "GeospatialInfoProviderResource requires either 'geospatial_map_v1_base_url' or 'dynamic_source_url' to be specified in the configuration."
            )

        self.client = specification.geospatial_info_provider.to_client(
            auth_adapter.adapter
        )
        self.participant_id = specification.geospatial_info_provider.participant_id
