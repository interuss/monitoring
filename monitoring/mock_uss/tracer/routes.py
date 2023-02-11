import datetime
import glob
import os
from typing import Dict, Tuple

import flask
from loguru import logger
from termcolor import colored
import yaml

from implicitdict import ImplicitDict
from monitoring.monitorlib import fetch, formatting, geo, infrastructure, versioning
from monitoring.monitorlib.fetch import summarize
import monitoring.monitorlib.fetch.rid
import monitoring.monitorlib.fetch.scd
from monitoring.mock_uss import webapp
from . import context


RESULT = ("", 204)


def _print_time_range(t0: str, t1: str) -> str:
    if not t0 and not t1:
        return ""
    now = datetime.datetime.utcnow()
    if t0.endswith("Z"):
        t0 = t0[0:-1]
    if t1.endswith("Z"):
        t1 = t1[0:-1]
    try:
        t0dt = datetime.datetime.fromisoformat(t0) - now
        t1dt = datetime.datetime.fromisoformat(t1) - now
        return " {} to {}".format(
            formatting.format_timedelta(t0dt), formatting.format_timedelta(t1dt)
        )
    except ValueError as e:
        return ""


@webapp.route(
    "/tracer/f3411v19/v1/uss/identification_service_areas/<id>", methods=["POST"]
)
def tracer_rid_v19_isa_notification(id: str) -> Tuple[str, int]:
    """Implements RID ISA notification receiver."""
    logger.debug(f"Handling tracer_rid_v19_isa_notification from {os.getpid()}")
    req = fetch.describe_flask_request(flask.request)
    req["endpoint"] = "identification_service_areas"
    log_name = context.resources.logger.log_new("notify_isa", req)

    claims = req.token
    owner = claims.get("sub", "<No owner in token>")
    label = colored("ISA", "cyan")
    try:
        json = flask.request.json
        if json.get("service_area"):
            isa = json["service_area"]
            owner_body = isa.get("owner")
            if owner_body and owner_body != owner:
                owner = "{} token|{} body".format(owner, owner_body)
            version = isa.get("version", "<Unknown version>")
            time_range = _print_time_range(isa.get("time_start"), isa.get("time_end"))
            logger.info(
                "{} {} v{} ({}) updated{} -> {}".format(
                    label, id, version, owner, time_range, log_name
                )
            )
        else:
            logger.info("{} {} ({}) deleted -> {}".format(label, id, owner, log_name))
    except ValueError as e:
        logger.error(
            "{} {} ({}) unable to decode JSON: {} -> {}".format(
                label, id, owner, e, log_name
            )
        )

    return RESULT


@webapp.route("/tracer/f3548v21/uss/v1/operational_intents", methods=["POST"])
def tracer_scd_v21_operation_notification() -> Tuple[str, int]:
    """Implements SCD Operation notification receiver."""
    logger.debug(f"Handling tracer_scd_v21_operation_notification from {os.getpid()}")
    req = fetch.describe_flask_request(flask.request)
    req["endpoint"] = "operational_intents"
    log_name = context.resources.logger.log_new("notify_op", req)

    claims = req.token
    owner = claims.get("sub", "<No owner in token>")
    label = colored("Operation", "blue")
    try:
        json = flask.request.json
        id = json.get("operational_intent_id", "<Unknown ID>")
        if json.get("operational_intent"):
            op = json["operational_intent"]
            version = "<Unknown version>"
            ovn = "<Unknown OVN>"
            time_range = ""
            if op.get("reference"):
                op_ref = op["reference"]
                owner_body = op_ref.get("owner")
                if owner_body and owner_body != owner:
                    owner = "{} token|{} body".format(owner, owner_body)
                version = op_ref.get("version", version)
                ovn = op_ref.get("ovn", ovn)
                time_range = _print_time_range(
                    op_ref.get("time_start", {}).get("value"),
                    op_ref.get("time_end", {}).get("value"),
                )
            state = "<Unknown state>"
            priority = 0
            if op.get("details"):
                op_details = op["details"]
                state = op_details.get("state")
                priority = op_details.get("priority", 0)
            priority_text = str(priority)
            logger.info(
                "{} {} {} {} v{} ({}) OVN[{}] updated{} -> {}".format(
                    label,
                    state,
                    priority_text,
                    id,
                    version,
                    owner,
                    ovn,
                    time_range,
                    log_name,
                )
            )
        else:
            logger.info("{} {} ({}) deleted -> {}".format(label, id, owner, log_name))
    except ValueError as e:
        logger.error(
            "{} ({}) unable to decode JSON: {} -> {}".format(label, owner, e, log_name)
        )

    return RESULT


@webapp.route("/tracer/f3548v21/uss/v1/constraints", methods=["POST"])
def tracer_scd_v21_constraint_notification() -> Tuple[str, int]:
    """Implements SCD Constraint notification receiver."""
    logger.debug(f"Handling tracer_scd_v21_constraint_notification from {os.getpid()}")
    req = fetch.describe_flask_request(flask.request)
    req["endpoint"] = "constraints"
    log_name = context.resources.logger.log_new("notify_constraint", req)

    claims = infrastructure.get_token_claims({k: v for k, v in flask.request.headers})
    owner = claims.get("sub", "<No owner in token>")
    label = colored("Constraint", "magenta")
    try:
        json = flask.request.json
        id = json.get("constraint_id", "<Unknown ID>")
        if json.get("constraint"):
            constraint = json["constraint"]
            version = "<Unknown version>"
            ovn = "<Unknown OVN>"
            time_range = ""
            if constraint.get("reference"):
                constraint_ref = constraint["reference"]
                owner_body = constraint_ref.get("owner")
                if owner_body and owner_body != owner:
                    owner = "{} token|{} body".format(owner, owner_body)
                version = constraint_ref.get("version", version)
                ovn = constraint_ref.get("ovn", ovn)
                time_range = _print_time_range(
                    constraint_ref.get("time_start", {}).get("value"),
                    constraint_ref.get("time_end", {}).get("value"),
                )
            type = "<Unspecified type>"
            if constraint.get("details"):
                constraint_details = constraint["details"]
                type = constraint_details.get("type")
            logger.info(
                "{} {} {} v{} ({}) OVN[{}] updated{} -> {}".format(
                    label, type, id, version, owner, ovn, time_range, log_name
                )
            )
        else:
            logger.info("{} {} ({}) deleted -> {}".format(label, id, owner, log_name))
    except ValueError as e:
        logger.error(
            "{} ({}) unable to decode JSON: {} -> {}".format(label, owner, e, log_name)
        )

    return RESULT


@webapp.route("/tracer/status")
def tracer_status():
    logger.debug(f"Handling tracer_status from {os.getpid()}")
    return "Tracer ok {}".format(versioning.get_code_version())


@webapp.route("/tracer/logs")
def tracer_list_logs():
    logger.debug(f"Handling tracer_list_logs from {os.getpid()}")
    logs = [
        log
        for log in reversed(sorted(os.listdir(context.resources.logger.log_path)))
        if log.endswith(".yaml")
    ]
    kmls = {}
    for log in logs:
        kml = os.path.join("kml", log[0:-5] + ".kml")
        if os.path.exists(os.path.join(context.resources.logger.log_path, kml)):
            kmls[log] = kml
    response = flask.make_response(
        flask.render_template("tracer/logs.html", logs=logs, kmls=kmls)
    )
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response


def _redact_and_augment_log(obj):
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k.lower() == "authorization" and isinstance(v, str):
                result[k] = {
                    "value": ".".join(v.split(".")[0:-1]) + ".REDACTED",
                    "claims": infrastructure.get_token_claims(obj),
                }
            else:
                result[k] = _redact_and_augment_log(v)
        return result
    elif isinstance(obj, str):
        return obj
    elif isinstance(obj, list):
        return [_redact_and_augment_log(item) for item in obj]
    else:
        return obj


@webapp.route("/tracer/logs/<log>")
def tracer_logs(log):
    logger.debug(f"Handling tracer_logs from {os.getpid()}")
    logfile = os.path.join(context.resources.logger.log_path, log)
    if not os.path.exists(logfile):
        flask.abort(404)
    with open(logfile, "r") as f:
        objs = [obj for obj in yaml.full_load_all(f)]
    if len(objs) == 1:
        obj = objs[0]
    else:
        obj = {"entries": objs}

    object_type = obj.get("object_type", None)
    if object_type == fetch.rid.FetchedISAs.__name__:
        obj = {
            "summary": summarize.isas(ImplicitDict.parse(obj, fetch.rid.FetchedISAs)),
            "details": obj,
        }
    elif object_type == fetch.scd.FetchedEntities.__name__:
        obj = {
            "summary": summarize.entities(
                ImplicitDict.parse(obj, fetch.scd.FetchedEntities)
            ),
            "details": obj,
        }
    elif object_type == fetch.rid.FetchedFlights.__name__:
        obj = {
            "summary": summarize.flights(
                ImplicitDict.parse(obj, fetch.rid.FetchedFlights)
            ),
            "details": obj,
        }

    return flask.render_template(
        "tracer/log.html", log=_redact_and_augment_log(obj), title=logfile
    )


@webapp.route("/tracer/kml/now.kml")
def tracer_kml_now():
    logger.debug(f"Handling tracer_kml_now from {os.getpid()}")
    all_kmls = glob.glob(
        os.path.join(context.resources.logger.log_path, "kml", "*.kml")
    )
    if not all_kmls:
        flask.abort(404, "No KMLs exist")
    latest_kml = max(all_kmls, key=os.path.getctime)
    return flask.send_file(
        latest_kml,
        mimetype="application/vnd.google-earth.kml+xml",
        attachment_filename="now.kml",
        as_attachment=True,
    )


@webapp.route("/tracer/kml/<kml>")
def tracer_kmls(kml):
    logger.debug(f"Handling tracer_kmls from {os.getpid()}")
    kmlfile = os.path.join(context.resources.logger.log_path, "kml", kml)
    if not os.path.exists(kmlfile):
        flask.abort(404)
    return flask.send_file(
        kmlfile,
        mimetype="application/vnd.google-earth.kml+xml",
        attachment_filename=kml,
        as_attachment=True,
    )


@webapp.route("/tracer/f3411v19/rid_poll", methods=["GET"])
def tracer_rid_v19_get_rid_poll():
    logger.debug(f"Handling tracer_rid_v19_get_rid_poll from {os.getpid()}")
    return flask.render_template("tracer/rid_poll.html")


@webapp.route("/tracer/f3411v19/rid_poll", methods=["POST"])
def tracer_rid_v19_request_rid_poll():
    logger.debug(f"Handling tracer_rid_v19_request_rid_poll from {os.getpid()}")
    if "area" not in flask.request.form:
        flask.abort(400, "Missing area")

    try:
        area = geo.make_latlng_rect(flask.request.form["area"])
    except ValueError as e:
        flask.abort(400, str(e))
        return

    flights_result = fetch.rid.all_flights(
        context.resources.dss_client,
        area,
        flask.request.form.get("include_recent_positions"),
        flask.request.form.get("get_details"),
        flask.request.form.get("enhanced_details"),
    )
    log_name = context.resources.logger.log_new(
        "clientrequest_getflights", flights_result
    )
    return flask.redirect(flask.url_for("tracer_logs", log=log_name))


@webapp.route("/tracer/<path:u_path>", methods=["GET", "PUT", "POST", "DELETE"])
def tracer_catch_all(u_path) -> Tuple[str, int]:
    logger.debug(f"Handling tracer_catch_all from {os.getpid()}")
    req = fetch.describe_flask_request(flask.request)
    req["endpoint"] = "catch_all"
    log_name = context.resources.logger.log_new("uss_badroute", req)

    claims = req.token
    owner = claims.get("sub", "<No owner in token>")
    label = colored("Bad route", "red")
    logger.error("{} to {} ({}): {}".format(label, u_path, owner, log_name))

    return RESULT
