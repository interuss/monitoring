from typing import Optional

from implicitdict import ImplicitDict
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from uas_standards.interuss.automated_testing.versioning import api
from uas_standards.interuss.automated_testing.versioning.constants import Scope

from monitoring.monitorlib.clients.versioning.client import (
    VersioningClient,
    VersionQueryError,
    GetVersionResponse,
)
from monitoring.monitorlib.fetch import query_and_describe, QueryType
from monitoring.monitorlib.infrastructure import UTMClientSession


class InterUSSVersioningClient(VersioningClient):
    def __init__(self, session: UTMClientSession, participant_id: ParticipantID):
        super(InterUSSVersioningClient, self).__init__(participant_id)
        self._session = session
        self._participant_id = participant_id

    def get_version(self, version_type: Optional[str]) -> GetVersionResponse:
        op = api.OPERATIONS[api.OperationID.GetVersion]
        kwargs = {
            "client": self._session,
            "verb": op.verb,
            "url": op.path.format(system_identity=version_type),
            "query_type": QueryType.InterUSSVersioningGetVersion,
            "scope": Scope.ReadSystemVersions,
        }
        if self._participant_id:
            kwargs["participant_id"] = self._participant_id
        query = query_and_describe(**kwargs)
        if query.status_code != 200:
            raise VersionQueryError(
                f"Attempt to get version returned status {query.status_code} rather than 200 as expected",
                query,
            )
        try:
            resp: api.GetVersionResponse = ImplicitDict.parse(
                query.response.json, api.GetVersionResponse
            )
        except ValueError as e:
            raise VersionQueryError(
                f"Response to get version could not be parsed: {str(e)}", query
            )
        if resp.system_identity != version_type:
            raise VersionQueryError(
                f"Response to get version indicated version for system '{resp.system_identity}' when the version for system '{version_type}' was requested"
            )
        return GetVersionResponse(version=resp.system_version, query=query)
