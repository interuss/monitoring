"""Test version can be queried."""

from monitoring.monitorlib import rid_v1

def test_version(aux_session):
  resp = aux_session.get('/version', scope=rid_v1.SCOPE_READ)
  assert resp.status_code == 200
  version = resp.json()['version']
  assert version
  assert 'undefined' not in version, version
