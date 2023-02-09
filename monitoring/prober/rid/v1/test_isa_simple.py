"""Basic ISA tests:

  - create the ISA with a 60 minute expiry
  - get by ID
  - search with earliest_time and latest_time
  - delete
"""

import datetime
import re

from monitoring.monitorlib.infrastructure import default_scope
from monitoring.monitorlib import rid_v1
from monitoring.monitorlib.rid_v1 import SCOPE_READ, SCOPE_WRITE, ISA_PATH
from monitoring.monitorlib.testing import assert_datetimes_are_equal
from monitoring.prober.infrastructure import register_resource_type
from . import common


ISA_TYPE = register_resource_type(223, 'ISA')


def test_ensure_clean_workspace(ids, session_ridv1):
  resp = session_ridv1.get('{}/{}'.format(ISA_PATH, ids(ISA_TYPE)), scope=SCOPE_READ)
  if resp.status_code == 200:
    version = resp.json()['service_area']['version']
    resp = session_ridv1.delete('{}/{}/{}'.format(ISA_PATH, ids(ISA_TYPE), version), scope=SCOPE_WRITE)
    assert resp.status_code == 200, resp.content
  elif resp.status_code == 404:
    # As expected.
    pass
  else:
    assert False, resp.content


@default_scope(SCOPE_WRITE)
def test_create_isa(ids, session_ridv1):
  """ASTM Compliance Test: DSS0030_A_PUT_ISA."""
  time_start = datetime.datetime.utcnow()
  time_end = time_start + datetime.timedelta(minutes=60)

  req_body = {
    'extents': {
      'spatial_volume': {
        'footprint': {
          'vertices': common.VERTICES,
        },
        'altitude_lo': 20,
        'altitude_hi': 400,
      },
      'time_start': time_start.strftime(rid_v1.DATE_FORMAT),
      'time_end': time_end.strftime(rid_v1.DATE_FORMAT),
    },
    'flights_url': 'https://example.com/dss',
  }
  resp = session_ridv1.put(
      '{}/{}'.format(ISA_PATH, ids(ISA_TYPE)),
      json=req_body)
  assert resp.status_code == 200, resp.content

  data = resp.json()
  assert data['service_area']['id'] == ids(ISA_TYPE)
  assert data['service_area']['flights_url'] == 'https://example.com/dss'
  assert_datetimes_are_equal(data['service_area']['time_start'], req_body['extents']['time_start'])
  assert_datetimes_are_equal(data['service_area']['time_end'], req_body['extents']['time_end'])
  assert re.match(r'[a-z0-9]{10,}$', data['service_area']['version'])
  assert 'subscribers' in data


@default_scope(SCOPE_READ)
def test_get_isa_by_id(ids, session_ridv1):
  resp = session_ridv1.get('{}/{}'.format(ISA_PATH, ids(ISA_TYPE)))
  assert resp.status_code == 200, resp.content

  data = resp.json()
  assert data['service_area']['id'] == ids(ISA_TYPE)
  assert data['service_area']['flights_url'] == 'https://example.com/dss'


@default_scope(SCOPE_WRITE)
def test_update_isa(ids, session_ridv1):
  resp = session_ridv1.get('{}/{}'.format(ISA_PATH, ids(ISA_TYPE)), scope=SCOPE_READ)
  version = resp.json()['service_area']['version']

  resp = session_ridv1.put(
    '{}/{}/{}'.format(ISA_PATH, ids(ISA_TYPE), version),
      json={
          'extents': {
              'spatial_volume': {
                  'footprint': {
                      'vertices': common.VERTICES,
                  },
                  'altitude_lo': 20,
                  'altitude_hi': 400,
              },
          },
          'flights_url': 'https://example.com/dss/v2',
      })
  assert resp.status_code == 200

  data = resp.json()
  assert data['service_area']['id'] == ids(ISA_TYPE)
  assert data['service_area']['flights_url'] == 'https://example.com/dss/v2'
  assert re.match(r'[a-z0-9]{10,}$', data['service_area']['version'])
  assert 'subscribers' in data


@default_scope(SCOPE_READ)
def test_get_isa_by_id_after_update(ids, session_ridv1):
  resp = session_ridv1.get('{}/{}'.format(ISA_PATH, ids(ISA_TYPE)))
  assert resp.status_code == 200, resp.content

  data = resp.json()
  assert data['service_area']['id'] == ids(ISA_TYPE)
  assert data['service_area']['flights_url'] == 'https://example.com/dss/v2'


@default_scope(SCOPE_READ)
def test_get_isa_by_search_missing_params(session_ridv1):
  resp = session_ridv1.get(ISA_PATH)
  assert resp.status_code == 400, resp.content


@default_scope(SCOPE_READ)
def test_get_isa_by_search(ids, session_ridv1):
  resp = session_ridv1.get('{}?area={}'.format(
      ISA_PATH, common.GEO_POLYGON_STRING))
  assert resp.status_code == 200, resp.content
  assert ids(ISA_TYPE) in [x['id'] for x in resp.json()['service_areas']]


@default_scope(SCOPE_READ)
def test_get_isa_by_search_earliest_time_included(ids, session_ridv1):
  earliest_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=59)
  resp = session_ridv1.get('{}?area={}&earliest_time={}'.format(
      ISA_PATH, common.GEO_POLYGON_STRING,
      earliest_time.strftime(rid_v1.DATE_FORMAT)))
  assert resp.status_code == 200, resp.content
  assert ids(ISA_TYPE) in [x['id'] for x in resp.json()['service_areas']]


@default_scope(SCOPE_READ)
def test_get_isa_by_search_earliest_time_excluded(ids, session_ridv1):
  earliest_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=61)
  resp = session_ridv1.get('{}?area={}&earliest_time={}'.format(
      ISA_PATH, common.GEO_POLYGON_STRING,
      earliest_time.strftime(rid_v1.DATE_FORMAT)))
  assert resp.status_code == 200, resp.content
  assert ids(ISA_TYPE) not in [x['id'] for x in resp.json()['service_areas']]


@default_scope(SCOPE_READ)
def test_get_isa_by_search_latest_time_included(ids, session_ridv1):
  latest_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=1)
  resp = session_ridv1.get('{}?area={}&latest_time={}'.format(
      ISA_PATH, common.GEO_POLYGON_STRING,
      latest_time.strftime(rid_v1.DATE_FORMAT)))
  assert resp.status_code == 200, resp.content
  assert ids(ISA_TYPE) in [x['id'] for x in resp.json()['service_areas']]


@default_scope(SCOPE_READ)
def test_get_isa_by_search_latest_time_excluded(ids, session_ridv1):
  latest_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
  resp = session_ridv1.get('{}?area={}&latest_time={}'.format(
      ISA_PATH, common.GEO_POLYGON_STRING,
      latest_time.strftime(rid_v1.DATE_FORMAT)))
  assert resp.status_code == 200, resp.content
  assert ids(ISA_TYPE) not in [x['id'] for x in resp.json()['service_areas']]


@default_scope(SCOPE_READ)
def test_get_isa_by_search_area_only(ids, session_ridv1):
  resp = session_ridv1.get('{}?area={}'.format(ISA_PATH, common.GEO_POLYGON_STRING))
  assert resp.status_code == 200, resp.content
  assert ids(ISA_TYPE) in [x['id'] for x in resp.json()['service_areas']]


@default_scope(SCOPE_READ)
def test_get_isa_by_search_huge_area(session_ridv1):
  resp = session_ridv1.get('{}?area={}'.format(ISA_PATH, common.HUGE_GEO_POLYGON_STRING))
  assert resp.status_code == 413, resp.content


@default_scope(SCOPE_WRITE)
def test_delete_isa_wrong_version(ids, session_ridv1):
  resp = session_ridv1.delete('{}/{}/fake_version'.format(ISA_PATH, ids(ISA_TYPE)))
  assert resp.status_code == 400, resp.content


@default_scope(SCOPE_WRITE)
def test_delete_isa_empty_version(ids, session_ridv1):
  resp = session_ridv1.delete('{}/{}/'.format(ISA_PATH, ids(ISA_TYPE)))
  assert resp.status_code == 400, resp.content


def test_delete_isa(ids, session_ridv1):
  """ASTM Compliance Test: DSS0030_B_DELETE_ISA."""
  # GET the ISA first to find its version.
  resp = session_ridv1.get('{}/{}'.format(ISA_PATH, ids(ISA_TYPE)), scope=SCOPE_READ)
  assert resp.status_code == 200, resp.content
  version = resp.json()['service_area']['version']

  # Then delete it.
  resp = session_ridv1.delete('{}/{}/{}'.format(ISA_PATH, ids(ISA_TYPE), version), scope=SCOPE_WRITE)
  assert resp.status_code == 200, resp.content


@default_scope(SCOPE_READ)
def test_get_deleted_isa_by_id(ids, session_ridv1):
  resp = session_ridv1.get('{}/{}'.format(ISA_PATH, ids(ISA_TYPE)))
  assert resp.status_code == 404, resp.content


@default_scope(SCOPE_READ)
def test_get_deleted_isa_by_search(ids, session_ridv1):
  resp = session_ridv1.get('{}?area={}'.format(ISA_PATH, common.GEO_POLYGON_STRING))
  assert resp.status_code == 200, resp.content
  assert ids(ISA_TYPE) not in [x['id'] for x in resp.json()['service_areas']]


@default_scope(SCOPE_READ)
def test_get_isa_search_area_with_loop(session_ridv1):
  resp = session_ridv1.get('{}?area={}'.format(ISA_PATH, common.LOOP_GEO_POLYGON_STRING))
  assert resp.status_code == 400, resp.content
