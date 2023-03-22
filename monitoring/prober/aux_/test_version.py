"""Test version can be queried."""

from monitoring.monitorlib import rid_v1
from uas_standards.astm.f3411 import v19


def test_version(aux_session):
    resp = aux_session.get("/version", scope=v19.constants.Scope.Read)
    assert resp.status_code == 200
    version = resp.json()["version"]
    assert version
    assert "undefined" not in version, version
