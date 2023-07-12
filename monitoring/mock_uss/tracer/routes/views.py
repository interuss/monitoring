import glob
import os

import flask
import monitoring.monitorlib.fetch.rid
import monitoring.monitorlib.fetch.scd
import yaml
from loguru import logger
from monitoring.mock_uss import webapp
from monitoring.monitorlib import fetch, geo, infrastructure
from monitoring.monitorlib.fetch import summarize

from implicitdict import ImplicitDict
from ..config import KEY_RID_VERSION

from .. import context

RID_VERSION = webapp.config[KEY_RID_VERSION]


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
        flask.render_template(
            "tracer/logs.html", logs=logs, kmls=kmls, rid_version=RID_VERSION.short_name
        )
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
        "tracer/log.html",
        log=_redact_and_augment_log(obj),
        title=logfile,
        rid_version=RID_VERSION.short_name,
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


@webapp.route("/tracer/rid/poll", methods=["GET"])
def tracer_rid_get_poll():
    logger.debug(f"Handling tracer_rid_get_poll from {os.getpid()}")
    return flask.render_template(
        "tracer/rid_poll.html", rid_version=RID_VERSION.short_name
    )


@webapp.route("/tracer/rid/poll", methods=["POST"])
def tracer_rid_request_poll():
    logger.debug(f"Handling tracer_rid_request_poll from {os.getpid()}")
    if "area" not in flask.request.form:
        flask.abort(400, "Missing area")

    try:
        area = geo.make_latlng_rect(flask.request.form["area"])
    except ValueError as err:
        flask.abort(400, str(err))
        return

    flights_result = fetch.rid.all_flights(
        area,
        flask.request.form.get("include_recent_positions"),
        flask.request.form.get("get_details"),
        RID_VERSION,
        context.resources.dss_clients["rid"],
        enhanced_details=flask.request.form.get("enhanced_details"),
    )
    log_name = context.resources.logger.log_new(
        "clientrequest_getflights", flights_result
    )
    return flask.redirect(flask.url_for("tracer_logs", log=log_name))
