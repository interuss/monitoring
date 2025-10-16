from monitoring.monitorlib.infrastructure import default_scope
from monitoring.monitorlib.scd import SCOPE_AA
from monitoring.prober.infrastructure import depends_on


def _get_uss_availability(uss_id, scd_session2):
    resp = scd_session2.get(f"/uss_availability/{uss_id}", scope=SCOPE_AA)
    assert resp.status_code == 200, resp.content
    data = resp.json()
    return data["status"]["uss"], data["status"]["availability"], data["version"]


@default_scope(SCOPE_AA)
def test_set_uss_availability(ids, scd_session2):
    resp = scd_session2.put(
        "/uss_availability/uss1", scope=SCOPE_AA, json={"availability": "normal"}
    )

    if resp.status_code == 409:
      # record already exists, retrieving version to mutate
      _, _, version = _get_uss_availability("uss1", scd_session2)
      resp = scd_session2.put(
        "/uss_availability/uss1", scope=SCOPE_AA, json={"availability": "normal", "old_version": version}
      )

    data = resp.json()
    assert data["status"]["uss"] == "uss1"
    assert data["status"]["availability"] == "Normal"
    assert data["version"]

    resp = scd_session2.put(
        "/uss_availability/uss1", scope=SCOPE_AA, json={"availability": "pUrPlE"}
    )
    assert resp.status_code == 400, resp.content


@default_scope(SCOPE_AA)
@depends_on(test_set_uss_availability)
def test_get_uss_availability(ids, scd_session2):
    uss, availability, version = _get_uss_availability("unknown_uss2", scd_session2)
    assert uss == "unknown_uss2"
    assert availability == "Unknown"
    assert version == ""

    uss, availability, version = _get_uss_availability("uss1", scd_session2)
    assert uss == "uss1"
    assert availability == "Normal"
    assert version
