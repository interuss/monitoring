from monitoring.monitorlib import scd
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.monitorlib.scd import SCOPE_CM, SCOPE_CP, SCOPE_SC


def _read_both_scope(scd_api: str) -> str:
    if scd_api == scd.API_0_3_17:
        return f"{str(SCOPE_SC)} {str(SCOPE_CP)}"
    else:
        raise NotImplementedError(f"Unsupported API version {scd_api}")


def delete_constraint_reference_if_exists(
    id: str, scd_session: UTMClientSession, scd_api: str
):
    resp = scd_session.get(f"/constraint_references/{id}", scope=SCOPE_CM)
    if resp.status_code == 200:
        if scd_api == scd.API_0_3_17:
            existing_constraint = resp.json().get("constraint_reference", None)
            resp = scd_session.delete(
                "/constraint_references/{}/{}".format(id, existing_constraint["ovn"]),
                scope=SCOPE_CM,
            )
        else:
            raise NotImplementedError(f"Unsupported API version {scd_api}")
        assert resp.status_code == 200, f"{resp.url}: {resp.content}"
    elif resp.status_code == 404:
        # As expected.
        pass
    else:
        assert False, resp.content


def delete_subscription_if_exists(
    sub_id: str, scd_session: UTMClientSession, scd_api: str
):
    resp = scd_session.get(f"/subscriptions/{sub_id}", scope=SCOPE_SC)
    if resp.status_code == 200:
        if scd_api == scd.API_0_3_17:
            sub = resp.json().get("subscription", None)
            resp = scd_session.delete(
                "/subscriptions/{}/{}".format(sub_id, sub["version"]),
                scope=_read_both_scope(scd_api),
            )
        else:
            raise NotImplementedError(f"Unsupported API version {scd_api}")
        assert resp.status_code == 200, resp.content
    elif resp.status_code == 404:
        # As expected.
        pass
    else:
        assert False, resp.content


def delete_operation_if_exists(id: str, scd_session: UTMClientSession, scd_api: str):
    if scd_api == scd.API_0_3_17:
        url = "/operational_intent_references/{}"
    else:
        assert False, f"Unsupported API {scd_api}"
    resp = scd_session.get(url.format(id), scope=SCOPE_SC)
    if resp.status_code == 200:
        if scd_api == scd.API_0_3_17:
            ovn = resp.json()["operational_intent_reference"]["ovn"]
            resp = scd_session.delete(f"/operational_intent_references/{id}/{ovn}")
        assert resp.status_code == 200, resp.content
    elif resp.status_code == 404:
        # As expected.
        pass
    else:
        assert False, f"Unsupported API {scd_api}"
