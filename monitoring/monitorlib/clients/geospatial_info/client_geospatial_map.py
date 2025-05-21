from typing import List, Optional, Dict, Any
import requests
import s2sphere
import geojson
from shapely.geometry import shape, Point

from implicitdict import ImplicitDict
from uas_standards.interuss.automated_testing.geospatial_map.v1.api import (
    OPERATIONS,
    GeospatialMapQueryReply,
    GeospatialMapQueryRequest,
    OperationID,
)
from uas_standards.interuss.automated_testing.geospatial_map.v1.constants import Scope

from monitoring.monitorlib.clients.geospatial_info.client import (
    GeospatialInfoClient,
    GeospatialInfoError,
)
from monitoring.monitorlib.clients.geospatial_info.querying import (
    GeospatialFeatureCheck,
    GeospatialFeatureCheckResult,
    GeospatialFeatureQueryResponse,
)
from monitoring.monitorlib.fetch import QueryType, query_and_describe
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.uss_qualifier.configurations.configuration import ParticipantID


class GeospatialMapClient(GeospatialInfoClient):
    _session: UTMClientSession
    _dynamic_source_url: Optional[str]
    _dynamic_source_type: Optional[str]
    _dynamic_source_interpretation_rule: Optional[str]

    def __init__(
        self,
        session: UTMClientSession,
        participant_id: ParticipantID,
        dynamic_source_url: Optional[str] = None,
        dynamic_source_type: Optional[str] = None,
        dynamic_source_interpretation_rule: Optional[str] = None,
    ):
        super(GeospatialMapClient, self).__init__(participant_id)
        self._session = session  # Primarily for existing geospatial map API calls
        self._dynamic_source_url = dynamic_source_url
        self._dynamic_source_type = dynamic_source_type
        self._dynamic_source_interpretation_rule = dynamic_source_interpretation_rule

    def query_geospatial_features(
        self, checks: List[GeospatialFeatureCheck]
    ) -> GeospatialFeatureQueryResponse:
        req_checks = [c.to_geospatial_map() for c in checks]

        op = OPERATIONS[OperationID.QueryGeospatialMap]
        req = GeospatialMapQueryRequest(checks=req_checks)
        query = query_and_describe(
            client=self._session,
            verb=op.verb,
            url=op.path,
            query_type=QueryType.InterUSSGeospatialMapV1QueryGeospatialMap,
            participant_id=self.participant_id,
            json=req,
            scope=Scope.Query,
        )
        if query.status_code != 200:
            raise GeospatialInfoError(
                f"Attempt to query geospatial map features returned status {query.status_code} rather than 200 as expected",
                query,
            )
        try:
            api_result = ImplicitDict.parse(
                query.response.json, GeospatialMapQueryReply
            )
        except ValueError as e:
            raise GeospatialInfoError(
                f"Response to geospatial map query could not be parsed: {str(e)}", query
            )

        # API-agnostic and API-specific response formats are currently wire-compatible
        results = [
            ImplicitDict.parse(r, GeospatialFeatureCheckResult)
            for r in api_result.results
        ]

        return GeospatialFeatureQueryResponse(
            queries=[query],
            results=results,
        )

    def get_dynamic_features(
        self, source_url: Optional[str] = None, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Fetches features from a dynamic GeoJSON source.
        If source_url is not provided, it uses the one from the configuration.
        `params` is currently not used but included for future flexibility.
        Returns a GeoJSON FeatureCollection as a dictionary.
        """
        url_to_fetch = source_url or self._dynamic_source_url
        if not url_to_fetch:
            raise GeospatialInfoError(
                "No source_url provided and no dynamic_source_url configured for the client."
            )

        # Note: We use self._session.client here to leverage existing session's retry mechanisms,
        # headers, etc., if applicable. If the dynamic source is always public and needs no
        # specific headers/auth from the session, requests.get() could be used directly.
        # However, using the session client might be beneficial for consistency or if
        # session-managed features like certs or specific proxies are in use.
        try:
            # TODO: query_and_describe uses a specific QueryType for reporting.
            # We may need a new QueryType for dynamic sources or a more generic one.
            # For now, using requests.get via the session's client directly.
            # The timeout can come from the session or be a default.
            response = self._session.get(
                url_to_fetch, timeout=self._session.timeout_s
            )
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
            return response.json()
        except requests.exceptions.RequestException as e:
            # Construct a dummy Query object for error reporting consistency, if possible
            # This part might need refinement based on how Query objects are typically constructed and used.
            # For now, we're creating a simplified representation.
            # query = Query(
            #     request=Request(method="GET", url=url_to_fetch),
            #     response=Response(status_code=response.status_code if 'response' in locals() else 0, content=response.content if 'response' in locals() else b""),
            #     errors=[str(e)]
            # )
            # For now, let's raise a simpler error, as Query object construction is complex.
            raise GeospatialInfoError(
                f"Failed to fetch dynamic GeoJSON from {url_to_fetch}: {e}", query=None
            ) # TODO: Create a query object for better error reporting
        except ValueError as e:  # Includes JSONDecodeError
            raise GeospatialInfoError(
                f"Failed to parse GeoJSON response from {url_to_fetch}: {e}", query=None
            ) # TODO: Create a query object for better error reporting

    def get_dynamic_test_points(
        self, source_url: Optional[str] = None, params: Optional[Dict[str, Any]] = None
    ) -> List[s2sphere.LatLng]:
        """
        Fetches features from a dynamic GeoJSON source and computes their centroids.
        If source_url is not provided, it uses the one from the configuration.
        `params` can include 'interpretation_rule', though currently defaults to 'treat_all_as_restrictions'.
        Returns a list of s2sphere.LatLng points (centroids).
        """
        geojson_data = self.get_dynamic_features(source_url, params)

        # Validate basic GeoJSON structure
        if not isinstance(geojson_data, dict) or geojson_data.get("type") != "FeatureCollection" or not isinstance(geojson_data.get("features"), list):
            url_fetched = source_url or self._dynamic_source_url
            raise GeospatialInfoError(
                f"Invalid GeoJSON FeatureCollection structure from {url_fetched}", query=None # TODO: query object
            )

        centroids: List[s2sphere.LatLng] = []
        # Default interpretation_rule: treat all features as restrictions and extract centroids
        # This could be made more sophisticated using `params` or `self._dynamic_source_interpretation_rule`
        
        for feature in geojson_data.get("features", []):
            if not isinstance(feature, dict) or feature.get("type") != "Feature" or "geometry" not in feature:
                # Potentially log a warning for malformed features
                continue

            try:
                geom = shape(feature["geometry"])
                centroid = geom.centroid
                # Ensure coordinates are in (lon, lat) order as expected by s2sphere.LatLng.from_degrees
                # Shapely's Point object has .x (longitude) and .y (latitude)
                centroids.append(s2sphere.LatLng.from_degrees(centroid.y, centroid.x))
            except Exception as e:
                # Log error during centroid calculation for a specific feature
                # For now, we'll skip features that cause errors.
                # Consider how to report these errors more formally if needed.
                print(f"Warning: Could not calculate centroid for feature: {feature.get('id', 'N/A')}. Error: {e}") # TODO: Use proper logging
                continue
        
        return centroids

    # TODO: The methods get_dynamic_features and get_dynamic_test_points currently use self._session.get
    # which is fine if the session is configured with a base_url that matches the dynamic_source_url.
    # However, dynamic_source_url can be arbitrary.
    # It might be cleaner to use a generic `requests.get()` call if no auth/session specific features
    # are needed for these public URLs. Or, ensure the session passed to GeospatialMapClient for dynamic
    # sources is correctly initialized (e.g. base_url set to the dynamic_source_url or empty if not needed).
    # The current implementation in GeospatialInfoProviderConfiguration uses dynamic_source_url as base_url
    # for the session when only dynamic source is configured, which should work.
