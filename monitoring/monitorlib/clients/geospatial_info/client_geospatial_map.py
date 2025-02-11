from typing import List

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

    def __init__(self, session: UTMClientSession, participant_id: ParticipantID):
        super(GeospatialMapClient, self).__init__(participant_id)
        self._session = session

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
