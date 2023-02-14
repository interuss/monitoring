"""Test subscriptions interact with ISAs:

  - Create an ISA.
  - Create a subscription, response should include the pre-existing ISA.
  - Modify the ISA, response should include the subscription.
  - Delete the ISA, response should include the subscription.
  - Delete the subscription.
"""

import datetime

from uas_standards.astm.f3411.v22a.api import OPERATIONS, OperationID
from uas_standards.astm.f3411.v22a.constants import Scope

from monitoring.monitorlib.infrastructure import default_scope
from monitoring.monitorlib import rid_v2
from monitoring.prober.infrastructure import register_resource_type
from . import common


ISA_PATH = OPERATIONS[OperationID.SearchIdentificationServiceAreas].path
SUBSCRIPTION_PATH = OPERATIONS[OperationID.SearchSubscriptions].path
ISA_TYPE = register_resource_type(364, 'ISA')
SUB_TYPE = register_resource_type(365, 'Subscription')
BASE_URL = 'https://example.com/rid/v2'


def test_ensure_clean_workspace(ids, session_ridv2):
  resp = session_ridv2.get('{}/{}'.format(ISA_PATH, ids(ISA_TYPE)), scope=Scope.DisplayProvider)
  if resp.status_code == 200:
    version = resp.json()['service_area']['version']
    resp = session_ridv2.delete('{}/{}/{}'.format(ISA_PATH, ids(ISA_TYPE), version), scope=Scope.ServiceProvider)
    assert resp.status_code == 200, resp.content
  elif resp.status_code == 404:
    # As expected.
    pass
  else:
    assert False, resp.content

  resp = session_ridv2.get('{}/{}'.format(SUBSCRIPTION_PATH, ids(SUB_TYPE)), scope=Scope.DisplayProvider)
  if resp.status_code == 200:
    version = resp.json()['subscription']['version']
    resp = session_ridv2.delete('{}/{}/{}'.format(SUBSCRIPTION_PATH, ids(SUB_TYPE), version), scope=Scope.DisplayProvider)
    assert resp.status_code == 200, resp.content
  elif resp.status_code == 404:
    # As expected
    pass
  else:
    assert False, resp.content


@default_scope(Scope.ServiceProvider)
def test_create_isa(ids, session_ridv2):
  time_start = datetime.datetime.utcnow()
  time_end = time_start + datetime.timedelta(minutes=60)

  resp = session_ridv2.put(
      '{}/{}'.format(ISA_PATH, ids(ISA_TYPE)),
      json={
          'extents': {
              'volume': {
                  'outline_polygon': {
                      'vertices': common.VERTICES,
                  },
                  'altitude_lower': rid_v2.make_altitude(20),
                  'altitude_upper': rid_v2.make_altitude(400),
              },
              'time_start': rid_v2.make_time(time_start),
              'time_end': rid_v2.make_time(time_end),
          },
          'uss_base_url': BASE_URL,
      })
  assert resp.status_code == 200, resp.content


@default_scope(Scope.DisplayProvider)
def test_create_subscription(ids, session_ridv2):
  time_start = datetime.datetime.utcnow()
  time_end = time_start + datetime.timedelta(minutes=60)

  resp = session_ridv2.put(
      '{}/{}'.format(SUBSCRIPTION_PATH, ids(SUB_TYPE)),
      json={
          'extents': {
              'volume': {
                  'outline_polygon': {
                      'vertices': common.VERTICES,
                  },
                  'altitude_lower': rid_v2.make_altitude(20),
                  'altitude_upper': rid_v2.make_altitude(400),
              },
              'time_start': rid_v2.make_time(time_start),
              'time_end': rid_v2.make_time(time_end),
          },
          'uss_base_url': BASE_URL,
      })
  assert resp.status_code == 200, resp.content

  # The response should include our ISA.
  data = resp.json()
  assert data['subscription']['notification_index'] == 0
  assert ids(ISA_TYPE) in [x['id'] for x in data['service_areas']]


def test_modify_isa(ids, session_ridv2):
  # GET the ISA first to find its version.
  resp = session_ridv2.get('{}/{}'.format(ISA_PATH, ids(ISA_TYPE)), scope=Scope.DisplayProvider)
  assert resp.status_code == 200, resp.content
  version = resp.json()['service_area']['version']

  # Then modify it.
  time_end = datetime.datetime.utcnow() + datetime.timedelta(minutes=60)
  resp = session_ridv2.put(
      '{}/{}/{}'.format(ISA_PATH, ids(ISA_TYPE), version),
      json={
          'extents': {
              'volume': {
                  'outline_polygon': {
                      'vertices': common.VERTICES,
                  },
                  'altitude_lower': rid_v2.make_altitude(12345),
                  'altitude_upper': rid_v2.make_altitude(67890),
              },
              'time_end': rid_v2.make_time(time_end),
          },
          'uss_base_url': BASE_URL,
      }, scope=Scope.ServiceProvider)
  assert resp.status_code == 200, resp.content

  # The response should include our subscription.
  data = resp.json()
  assert {
      'url': BASE_URL,
      'subscriptions': [{
          'notification_index': 1,
          'subscription_id': ids(SUB_TYPE),
      },],
  } in data['subscribers']


def test_delete_isa(ids, session_ridv2):
  # GET the ISA first to find its version.
  resp = session_ridv2.get('{}/{}'.format(ISA_PATH, ids(ISA_TYPE)), scope=Scope.DisplayProvider)
  assert resp.status_code == 200, resp.content
  version = resp.json()['service_area']['version']

  # Then delete it.
  resp = session_ridv2.delete('{}/{}/{}'.format(
      ISA_PATH, ids(ISA_TYPE), version), scope=Scope.ServiceProvider)
  assert resp.status_code == 200, resp.content

  # The response should include our subscription.
  data = resp.json()
  assert {
      'url': BASE_URL,
      'subscriptions': [{
          'notification_index': 2,
          'subscription_id': ids(SUB_TYPE),
      },],
  } in data['subscribers']


@default_scope(Scope.DisplayProvider)
def test_delete_subscription(ids, session_ridv2):
  # GET the sub first to find its version.
  resp = session_ridv2.get('{}/{}'.format(SUBSCRIPTION_PATH, ids(SUB_TYPE)))
  assert resp.status_code == 200, resp.content

  data = resp.json()
  version = data['subscription']['version']
  assert data['subscription']['notification_index'] == 2

  # Then delete it.
  resp = session_ridv2.delete('{}/{}/{}'.format(SUBSCRIPTION_PATH, ids(SUB_TYPE), version))
  assert resp.status_code == 200, resp.content
