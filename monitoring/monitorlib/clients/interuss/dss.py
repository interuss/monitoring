# Monkeypatch StringBasedDateTime in implicitdict before importing uas_standards.interuss.dss.aux.api
import implicitdict
_orig_stringbaseddatetime_new = implicitdict.StringBasedDateTime.__new__
def _patched_stringbaseddatetime_new(cls, value):
    if not value:
        value = "1970-01-01T00:00:00Z"
    return _orig_stringbaseddatetime_new(cls, value)
implicitdict.StringBasedDateTime.__new__ = _patched_stringbaseddatetime_new

from implicitdict import ImplicitDict
from uas_standards.interuss.dss.aux import api
from uas_standards.interuss.dss.aux.constants import Scope

from monitoring.monitorlib.fetch import Query, QueryError, QueryType, query_and_describe
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.uss_qualifier.configurations.configuration import ParticipantID


class InterUSSDSSClient:
    def __init__(self, session: UTMClientSession, participant_id: ParticipantID):
        self._session = session
        self._participant_id = participant_id

    def get_pool(self) -> tuple[api.PoolResponse, Query]:
        op = api.OPERATIONS[api.OperationID.GetPool]
        kwargs = {
            "client": self._session,
            "verb": op.verb,
            "url": op.path,
            "query_type": QueryType.InterUSSDSSGetPool,
            "scope": Scope.PoolStatusRead,
        }
        if self._participant_id:
            kwargs["participant_id"] = self._participant_id
        query = query_and_describe(**kwargs)
        if query.status_code != 200:
            raise QueryError(
                f"Attempt to get pool info returned status {query.status_code} rather than 200 as expected",
                query,
            )
        try:
            resp: api.PoolResponse = ImplicitDict.parse(
                query.response.json, api.PoolResponse
            )
        except ValueError as e:
            raise QueryError(
                f"Response to get pool info could not be parsed: {str(e)}", query
            )
        return resp, query

    def get_dss_instances(self) -> tuple[api.DSSInstancesResponse, Query]:
        op = api.OPERATIONS[api.OperationID.GetDSSInstances]
        kwargs = {
            "client": self._session,
            "verb": op.verb,
            "url": op.path,
            "query_type": QueryType.InterUSSDSSGetDSSInstances,
            "scope": Scope.PoolStatusRead,
        }
        if self._participant_id:
            kwargs["participant_id"] = self._participant_id
        query = query_and_describe(**kwargs)
        if query.status_code != 200:
            raise QueryError(
                f"Attempt to get DSS instances returned status {query.status_code} rather than 200 as expected",
                query,
            )
        try:
            resp: api.DSSInstancesResponse = ImplicitDict.parse(
                query.response.json, api.DSSInstancesResponse
            )
        except ValueError as e:
            raise QueryError(
                f"Response to get DSS instances could not be parsed: {str(e)}", query
            )
        return resp, query

    def get_accepted_ca_certs(self) -> tuple[api.CAsResponse, Query]:
        op = api.OPERATIONS[api.OperationID.GetAcceptedCAs]
        kwargs = {
            "client": self._session,
            "verb": op.verb,
            "url": op.path,
            "query_type": QueryType.InterUSSDSSGetAcceptedCAs,
            "scope": Scope.PoolStatusRead,
        }
        if self._participant_id:
            kwargs["participant_id"] = self._participant_id
        query = query_and_describe(**kwargs)
        if query.status_code != 200:
            raise QueryError(
                f"Attempt to get accepted CA certs returned status {query.status_code} rather than 200 as expected",
                query,
            )
        try:
            resp: api.CAsResponse = ImplicitDict.parse(
                query.response.json, api.CAsResponse
            )
        except ValueError as e:
            raise QueryError(
                f"Response to get accepted CA certs could not be parsed: {str(e)}", query
            )
        return resp, query

    def get_instance_ca_certs(self) -> tuple[api.CAsResponse, Query]:
        op = api.OPERATIONS[api.OperationID.GetInstanceCAs]
        kwargs = {
            "client": self._session,
            "verb": op.verb,
            "url": op.path,
            "query_type": QueryType.InterUSSDSSGetInstanceCAs,
            "scope": Scope.PoolStatusRead,
        }
        if self._participant_id:
            kwargs["participant_id"] = self._participant_id
        query = query_and_describe(**kwargs)
        if query.status_code != 200:
            raise QueryError(
                f"Attempt to get instance CA certs returned status {query.status_code} rather than 200 as expected",
                query,
            )
        try:
            resp: api.CAsResponse = ImplicitDict.parse(
                query.response.json, api.CAsResponse
            )
        except ValueError as e:
            raise QueryError(
                f"Response to get instance CA certs could not be parsed: {str(e)}", query
            )
        return resp, query
