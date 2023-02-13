"""Test subscriptions interact with ISAs:

  - Create an ISA.
  - Create a subscription, response should include the pre-existing ISA.
  - Modify the ISA, response should include the subscription.
  - Delete the ISA, response should include the subscription.
  - Delete the subscription.
"""

import datetime

from monitoring.monitorlib.infrastructure import default_scope
from monitoring.monitorlib import rid_v1
from monitoring.prober.infrastructure import register_resource_type
from . import common

from uas_standards.astm.f3411.v19.api import OPERATIONS, OperationID
from uas_standards.astm.f3411.v19.constants import Scope

ISA_PATH = OPERATIONS[OperationID.SearchIdentificationServiceAreas].path
SUBSCRIPTION_PATH = OPERATIONS[OperationID.SearchSubscriptions].path
ISA_TYPE = register_resource_type(325, 'ISA')
SUB_TYPE = register_resource_type(326, 'Subscription')


def test_ensure_clean_workspace(ids, session_ridv1):
  resp = session_ridv1.get('{}/{}'.format(ISA_PATH, ids(ISA_TYPE)), scope=Scope.Read)
  if resp.status_code == 200:
    version = resp.json()['service_area']['version']
    resp = session_ridv1.delete('{}/{}/{}'.format(ISA_PATH, ids(ISA_TYPE), version), scope=Scope.Write)
    assert resp.status_code == 200, resp.content
  elif resp.status_code == 404:
    # As expected.
    pass
  else:
    assert False, resp.content

  resp = session_ridv1.get('{}/{}'.format(SUBSCRIPTION_PATH, ids(SUB_TYPE)), scope=Scope.Read)
  if resp.status_code == 200:
    version = resp.json()['subscription']['version']
    resp = session_ridv1.delete('{}/{}/{}'.format(SUBSCRIPTION_PATH, ids(SUB_TYPE), version), scope=Scope.Read)
    assert resp.status_code == 200, resp.content
  elif resp.status_code == 404:
    # As expected
    pass
  else:
    assert False, resp.content


@default_scope(Scope.Write)
def test_create_isa(ids, session_ridv1):
  time_start = datetime.datetime.utcnow()
  time_end = time_start + datetime.timedelta(minutes=60)

  resp = session_ridv1.put(
      '{}/{}'.format(ISA_PATH, ids(ISA_TYPE)),
      json={
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
      })
  assert resp.status_code == 200, resp.content


@default_scope(Scope.Read)
def test_create_subscription(ids, session_ridv1):
  time_start = datetime.datetime.utcnow()
  time_end = time_start + datetime.timedelta(minutes=60)

  resp = session_ridv1.put(
      '{}/{}'.format(SUBSCRIPTION_PATH, ids(SUB_TYPE)),
      json={
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
          'callbacks': {
              'identification_service_area_url': 'https://example.com/foo'
          },
      })
  assert resp.status_code == 200, resp.content

  # The response should include our ISA.
  data = resp.json()
  assert data['subscription']['notification_index'] == 0
  assert ids(ISA_TYPE) in [x['id'] for x in data['service_areas']]


def test_modify_isa(ids, session_ridv1):
  # GET the ISA first to find its version.
  resp = session_ridv1.get('{}/{}'.format(ISA_PATH, ids(ISA_TYPE)), scope=Scope.Read)
  assert resp.status_code == 200, resp.content
  version = resp.json()['service_area']['version']

  # Then modify it.
  time_end = datetime.datetime.utcnow() + datetime.timedelta(minutes=60)
  resp = session_ridv1.put(
      '{}/{}/{}'.format(ISA_PATH, ids(ISA_TYPE), version),
      json={
          'extents': {
              'spatial_volume': {
                  'footprint': {
                      'vertices': common.VERTICES,
                  },
                  'altitude_lo': 12345,
                  'altitude_hi': 67890,
              },

              'time_end': time_end.strftime(rid_v1.DATE_FORMAT),
          },
          'flights_url': 'https://example.com/dss',
      }, scope=Scope.Write)
  assert resp.status_code == 200, resp.content

  # The response should include our subscription.
  data = resp.json()
  assert {
      'url':
          'https://example.com/foo',
      'subscriptions': [{
          'notification_index': 1,
          'subscription_id': ids(SUB_TYPE),
      },],
  } in data['subscribers']


def test_delete_isa(ids, session_ridv1):
  # GET the ISA first to find its version.
  resp = session_ridv1.get('{}/{}'.format(ISA_PATH, ids(ISA_TYPE)), scope=Scope.Read)
  assert resp.status_code == 200, resp.content
  version = resp.json()['service_area']['version']

  # Then delete it.
  resp = session_ridv1.delete('{}/{}/{}'.format(
      ISA_PATH, ids(ISA_TYPE), version), scope=Scope.Write)
  assert resp.status_code == 200, resp.content

  # The response should include our subscription.
  data = resp.json()
  assert {
      'url':
          'https://example.com/foo',
      'subscriptions': [{
          'notification_index': 2,
          'subscription_id': ids(SUB_TYPE),
      },],
  } in data['subscribers']


@default_scope(Scope.Read)
def test_delete_subscription(ids, session_ridv1):
  # GET the sub first to find its version.
  resp = session_ridv1.get('{}/{}'.format(SUBSCRIPTION_PATH, ids(SUB_TYPE)))
  assert resp.status_code == 200, resp.content

  data = resp.json()
  version = data['subscription']['version']
  assert data['subscription']['notification_index'] == 2

  # Then delete it.
  resp = session_ridv1.delete('{}/{}/{}'.format(SUBSCRIPTION_PATH, ids(SUB_TYPE), version))
  assert resp.status_code == 200, resp.content
