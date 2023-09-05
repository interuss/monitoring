from typing import List, Optional, Tuple

from monitoring.monitorlib import fetch, scd
from monitoring.monitorlib.fetch import QueryError, Query
from monitoring.monitorlib.infrastructure import UTMClientSession
from implicitdict import ImplicitDict
from monitoring.monitorlib.clients import call_query_hooks
from monitoring.monitorlib.mock_uss_interface.interaction_log import Issue

# === DSS operations defined in ASTM API ===


def query_operational_intent_references(
    utm_client: UTMClientSession, area_of_interest: scd.Volume4D
) -> List[scd.OperationalIntentReference]:
    url = "/dss/v1/operational_intent_references/query"
    subject = f"queryOperationalIntentReferences from {url}"
    req = scd.QueryOperationalIntentReferenceParameters(
        area_of_interest=area_of_interest
    )
    query = fetch.query_and_describe(
        utm_client, "POST", url, json=req, scope=scd.SCOPE_SC
    )
    if query.status_code != 200:
        raise QueryError(
            msg="{} failed {}:\n{}".format(
                subject, query.status_code, query.response.get("content", "")
            ),
            queries=[query],
        )
    try:
        resp_body = ImplicitDict.parse(
            query.response.json, scd.QueryOperationalIntentReferenceResponse
        )
    except KeyError:
        raise QueryError(
            msg=f"{subject} response did not contain JSON body", queries=[query]
        )
    except ValueError as e:
        raise QueryError(
            msg=f"{subject} response contained invalid JSON: {str(e)}", queries=[query]
        )
    return resp_body.operational_intent_references


def create_operational_intent_reference(
    utm_client: UTMClientSession,
    id: str,
    req: scd.PutOperationalIntentReferenceParameters,
) -> scd.ChangeOperationalIntentReferenceResponse:
    url = "/dss/v1/operational_intent_references/{}".format(id)
    subject = f"createOperationalIntentReference to {url}"
    query = fetch.query_and_describe(
        utm_client, "PUT", url, json=req, scope=scd.SCOPE_SC
    )
    if query.status_code != 200 and query.status_code != 201:
        raise QueryError(
            msg="{} failed {}:\n{}".format(
                subject, query.status_code, query.response.get("content", "")
            ),
            queries=[query],
        )
    try:
        return ImplicitDict.parse(
            query.response.json, scd.ChangeOperationalIntentReferenceResponse
        )
    except KeyError:
        raise QueryError(
            msg=f"{subject} response did not contain JSON body", queries=[query]
        )
    except ValueError as e:
        raise QueryError(
            msg=f"{subject} response contained invalid JSON: {str(e)}", queries=[query]
        )


def update_operational_intent_reference(
    utm_client: UTMClientSession,
    id: str,
    ovn: str,
    req: scd.PutOperationalIntentReferenceParameters,
) -> scd.ChangeOperationalIntentReferenceResponse:
    url = "/dss/v1/operational_intent_references/{}/{}".format(id, ovn)
    subject = f"updateOperationalIntentReference to {url}"
    query = fetch.query_and_describe(
        utm_client, "PUT", url, json=req, scope=scd.SCOPE_SC
    )
    if query.status_code != 200 and query.status_code != 201:
        raise QueryError(
            msg="{} failed {}:\n{}".format(
                subject, query.status_code, query.response.get("content", "")
            ),
            queries=[query],
        )
    try:
        return ImplicitDict.parse(
            query.response.json, scd.ChangeOperationalIntentReferenceResponse
        )
    except KeyError:
        raise QueryError(
            msg=f"{subject} response did not contain JSON body", queries=[query]
        )
    except ValueError as e:
        raise QueryError(
            msg=f"{subject} response contained invalid JSON: {str(e)}", queries=[query]
        )


def delete_operational_intent_reference(
    utm_client: UTMClientSession, id: str, ovn: str
) -> scd.ChangeOperationalIntentReferenceResponse:
    url = f"/dss/v1/operational_intent_references/{id}/{ovn}"
    subject = f"deleteOperationalIntentReference from {url}"
    query = fetch.query_and_describe(utm_client, "DELETE", url, scope=scd.SCOPE_SC)
    if query.status_code != 200:
        raise QueryError(
            msg="{} failed {}:\n{}".format(
                subject, query.status_code, query.response.get("content", "")
            ),
            queries=[query],
        )
    try:
        return ImplicitDict.parse(
            query.response.json, scd.ChangeOperationalIntentReferenceResponse
        )
    except KeyError:
        raise QueryError(
            msg=f"{subject} response did not contain JSON body", queries=[query]
        )
    except ValueError as e:
        raise QueryError(
            msg=f"{subject} response contained invalid JSON: {str(e)}", queries=[query]
        )


# === USS operations defined in the ASTM API ===


def get_operational_intent_details(
    utm_client: UTMClientSession, uss_base_url: str, id: str
) -> Tuple[scd.OperationalIntent, Query]:

    try:
        op_intent, query = get_operational_intent_details_with_query_hook(
            utm_client, uss_base_url, id
        )
        call_query_hooks(query=query, function=get_operational_intent_details)
    except QueryError as q:
        call_query_hooks(
            query=q.queries[0],
            function=get_operational_intent_details,
            issues=[Issue(q.msg)],
        )
        raise q
    return op_intent, query


def get_operational_intent_details_with_query_hook(
    utm_client: UTMClientSession, uss_base_url: str, id: str
) -> Tuple[scd.OperationalIntent, Query]:
    url = f"{uss_base_url}/uss/v1/operational_intents/{id}"
    subject = f"getOperationalIntentDetails from {url}"

    query = fetch.query_and_describe(utm_client, "GET", url, scope=scd.SCOPE_SC)
    if query.status_code != 200:
        raise QueryError(
            msg="{} failed {}:\n{}".format(
                subject, query.status_code, query.response.get("content", "")
            ),
            queries=[query],
        )
    try:
        resp_body = ImplicitDict.parse(
            query.response.json, scd.GetOperationalIntentDetailsResponse
        )
    except KeyError:
        raise QueryError(
            msg=f"{subject} response did not contain JSON body", queries=[query]
        )
    except ValueError as e:
        raise QueryError(
            msg=f"{subject} response contained invalid JSON: {str(e)}", queries=[query]
        )
    return resp_body.operational_intent, query


def notify_operational_intent_details_changed(
    utm_client: UTMClientSession,
    uss_base_url: str,
    update: scd.PutOperationalIntentDetailsParameters,
):
    try:
        query = notify_operational_intent_details_with_query_hook(
            utm_client, uss_base_url, update
        )
        call_query_hooks(
            query=query, function=notify_operational_intent_details_changed
        )
    except QueryError as q:
        call_query_hooks(
            query=q.queries[0],
            function=get_operational_intent_details,
            issues=[Issue(q.msg)],
        )
        raise q


def notify_operational_intent_details_with_query_hook(
    utm_client: UTMClientSession,
    uss_base_url: str,
    update: scd.PutOperationalIntentDetailsParameters,
) -> Query:

    url = f"{uss_base_url}/uss/v1/operational_intents"
    subject = f"notifyOperationalIntentDetailsChanged to {url}"
    query = fetch.query_and_describe(
        utm_client, "POST", url, json=update, scope=scd.SCOPE_SC
    )
    if query.status_code != 204 and query.status_code != 200:
        raise QueryError(
            msg="{} failed {}:\n{}".format(
                subject, query.status_code, query.response.get("content", "")
            ),
            queries=[query],
        )
    return query


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
