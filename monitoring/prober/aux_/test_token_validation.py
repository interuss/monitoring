"""Test aux features"""

from uas_standards.astm.f3411.v19.constants import Scope

from monitoring.monitorlib.infrastructure import default_scope


@default_scope(Scope.Read)
def test_validate(aux_session):
    resp = aux_session.get("/validate_oauth")
    assert resp.status_code == 200


@default_scope(Scope.Read)
def test_validate_token_good_user(aux_session, subscriber):
    resp = aux_session.get("/validate_oauth?owner={}".format(subscriber))
    assert resp.status_code == 200


@default_scope(Scope.Read)
def test_validate_token_bad_user(aux_session):
    resp = aux_session.get("/validate_oauth?owner=bad_user")
    assert resp.status_code == 403
