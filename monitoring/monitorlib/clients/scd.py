from datetime import datetime
from typing import List, Optional

from monitoring.monitorlib import fetch, scd
from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.infrastructure import UTMClientSession
from implicitdict import ImplicitDict


# === DSS operations defined in ASTM API ===


def query_operational_intent_references(
    utm_client: UTMClientSession, area_of_interest: scd.Volume4D
) -> List[scd.OperationalIntentReference]:
    req = scd.QueryOperationalIntentReferenceParameters(
        area_of_interest=area_of_interest
    )
    initiated_at = datetime.utcnow()
    resp = utm_client.post(
        "/dss/v1/operational_intent_references/query", json=req, scope=scd.SCOPE_SC
    )
    query = fetch.describe_query(resp, initiated_at)
    if resp.status_code != 200:
        raise QueryError(
            msg="queryOperationalIntentReferences failed {}:\n{}".format(
                resp.status_code, resp.content.decode("utf-8")
            ),
            queries=[query],
        )
    resp_body = ImplicitDict.parse(
        resp.json(), scd.QueryOperationalIntentReferenceResponse
    )
    return resp_body.operational_intent_references


def create_operational_intent_reference(
    utm_client: UTMClientSession,
    id: str,
    req: scd.PutOperationalIntentReferenceParameters,
) -> scd.ChangeOperationalIntentReferenceResponse:
    url = "/dss/v1/operational_intent_references/{}".format(id)
    initiated_at = datetime.utcnow()
    resp = utm_client.put(url, json=req, scope=scd.SCOPE_SC)
    query = fetch.describe_query(resp, initiated_at)
    if resp.status_code != 200 and resp.status_code != 201:
        raise QueryError(
            msg="createOperationalIntentReference failed {} to {}:\n{}".format(
                resp.status_code, url, resp.content.decode("utf-8")
            ),
            queries=[query],
        )
    return ImplicitDict.parse(resp.json(), scd.ChangeOperationalIntentReferenceResponse)


def update_operational_intent_reference(
    utm_client: UTMClientSession,
    id: str,
    ovn: str,
    req: scd.PutOperationalIntentReferenceParameters,
) -> scd.ChangeOperationalIntentReferenceResponse:
    url = "/dss/v1/operational_intent_references/{}/{}".format(id, ovn)
    initiated_at = datetime.utcnow()
    resp = utm_client.put(url, json=req, scope=scd.SCOPE_SC)
    query = fetch.describe_query(resp, initiated_at)
    if resp.status_code != 200 and resp.status_code != 201:
        raise QueryError(
            msg="updateOperationalIntentReference failed {} to {}:\n{}".format(
                resp.status_code, url, resp.content.decode("utf-8")
            ),
            queries=[query],
        )
    return ImplicitDict.parse(resp.json(), scd.ChangeOperationalIntentReferenceResponse)


def delete_operational_intent_reference(
    utm_client: UTMClientSession, id: str, ovn: str
) -> scd.ChangeOperationalIntentReferenceResponse:
    initiated_at = datetime.utcnow()
    resp = utm_client.delete(
        "/dss/v1/operational_intent_references/{}/{}".format(id, ovn),
        scope=scd.SCOPE_SC,
    )
    query = fetch.describe_query(resp, initiated_at)
    if resp.status_code != 200:
        raise QueryError(
            msg="deleteOperationalIntentReference failed {}:\n{}".format(
                resp.status_code, resp.content.decode("utf-8")
            ),
            queries=[query],
        )
    return ImplicitDict.parse(resp.json(), scd.ChangeOperationalIntentReferenceResponse)


# === USS operations defined in the ASTM API ===


def get_operational_intent_details(
    utm_client: UTMClientSession, uss_base_url: str, id: str
) -> scd.OperationalIntent:
    initiated_at = datetime.utcnow()
    resp = utm_client.get(
        "{}/uss/v1/operational_intents/{}".format(uss_base_url, id), scope=scd.SCOPE_SC
    )
    query = fetch.describe_query(resp, initiated_at)
    if resp.status_code != 200:
        raise QueryError(
            msg="getOperationalIntentDetails failed {}:\n{}".format(
                resp.status_code, resp.content.decode("utf-8")
            ),
            queries=[query],
        )
    resp_body = ImplicitDict.parse(resp.json(), scd.GetOperationalIntentDetailsResponse)
    return resp_body.operational_intent


def notify_operational_intent_details_changed(
    utm_client: UTMClientSession,
    uss_base_url: str,
    update: scd.PutOperationalIntentDetailsParameters,
) -> None:
    initiated_at = datetime.utcnow()
    resp = utm_client.post(
        "{}/uss/v1/operational_intents".format(uss_base_url),
        json=update,
        scope=scd.SCOPE_SC,
    )
    query = fetch.describe_query(resp, initiated_at)
    if resp.status_code != 204 and resp.status_code != 200:
        raise QueryError(
            msg="notifyOperationalIntentDetailsChanged failed {} to {}:\n{}".format(
                resp.status_code, resp.request.url, resp.content.decode("utf-8")
            ),
            queries=[query],
        )


# === Custom actions ===


def notify_subscribers(
    utm_client: UTMClientSession,
    id: str,
    operational_intent: Optional[scd.OperationalIntent],
    subscribers: List[scd.SubscriberToNotify],
):
    for subscriber in subscribers:
        kwargs = {
            "operational_intent_id": id,
            "subscriptions": subscriber.subscriptions,
        }
        if operational_intent is not None:
            kwargs["operational_intent"] = operational_intent
        update = scd.PutOperationalIntentDetailsParameters(**kwargs)
        notify_operational_intent_details_changed(
            utm_client, subscriber.uss_base_url, update
        )
