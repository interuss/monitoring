import datetime
import glob
import io
import os
import zipfile
from typing import cast

import arrow
import flask
import flask_login
import yaml
from implicitdict import ImplicitDict, StringBasedDateTime
from loguru import logger

from monitoring.mock_uss.app import webapp
from monitoring.mock_uss.tracer import context
from monitoring.mock_uss.tracer.database import db
from monitoring.mock_uss.tracer.kml import render_historical_kml
from monitoring.mock_uss.tracer.log_types import PollFlights, TracerLogEntry
from monitoring.mock_uss.tracer.observation_areas import ObservationArea
from monitoring.mock_uss.ui import auth as ui_auth
from monitoring.monitorlib import geo, infrastructure
from monitoring.monitorlib.fetch import rid


@webapp.route("/tracer/logs", methods=["GET"])
@ui_auth.login_required()
def tracer_list_logs():
    logger.debug(f"Handling tracer_list_logs from {os.getpid()}")
    logs = [
        log
        for log in reversed(sorted(os.listdir(context.tracer_logger.log_path)))
        if log.endswith(".yaml")
    ]
    kmls = {}
    for log in logs:
        kml = os.path.join("kml", log[0:-5] + ".kml")
        if os.path.exists(os.path.join(context.tracer_logger.log_path, kml)):
            kmls[log] = kml
    response = flask.make_response(
        flask.render_template(
            "tracer/logs.html",
            logs=logs,
            kmls=kmls,
            current_user=flask_login.current_user,
        )
    )
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response


@webapp.route("/tracer/logs.zip")
@ui_auth.login_required(role="admin")
def tracer_download_logs():
    logs = [
        log
        for log in reversed(sorted(os.listdir(context.tracer_logger.log_path)))
        if log.endswith(".yaml")
    ]
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for log in logs:
            with open(os.path.join(context.tracer_logger.log_path, log)) as f:
                zip_file.writestr(log, f.read())
    zip_name = (
        f"logs_{datetime.datetime.now(datetime.UTC).isoformat().split('.')[0]}.zip"
    )
    return flask.Response(
        zip_buffer.getvalue(),
        mimetype="application/zip",
        headers={"Content-Disposition": f"attachment;filename={zip_name}"},
    )


@webapp.route("/tracer/logs", methods=["DELETE"])
@ui_auth.login_required(role="admin")
def tracer_clear_logs():
    if db.value.observation_areas:
        return "Logs cannot be cleared while any observation areas exist", 400

    files = [
        f
        for f in reversed(sorted(os.listdir(context.tracer_logger.log_path)))
        if f.endswith(".yaml") or f.endswith(".kml")
    ]
    for f in files:
        os.remove(os.path.join(context.tracer_logger.log_path, f))
    return f"{len(files)} log files cleared successfully", 200


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
@ui_auth.login_required()
def tracer_logs(log):
    logger.debug(f"Handling tracer_logs from {os.getpid()}")
    logfile = os.path.join(context.tracer_logger.log_path, log)
    if not os.path.exists(logfile):
        flask.abort(404)
    with open(logfile) as f:
        objs = [obj for obj in yaml.full_load_all(f)]
    if len(objs) == 1:
        obj = objs[0]
    else:
        obj = {"entries": objs}

    object_type_name = cast(str | None, obj.get("object_type", None))
    object_type = TracerLogEntry.entry_type(object_type_name)
    if object_type:
        parsed: TracerLogEntry = ImplicitDict.parse(obj, object_type)
        obj = parsed.human_info()

    return flask.render_template(
        "tracer/log.html",
        log=_redact_and_augment_log(obj),
        title=logfile,
        username=flask_login.current_user.username,
    )


@webapp.route("/tracer/kml/now.kml")
@ui_auth.login_required()
def tracer_kml_now():
    logger.debug(f"Handling tracer_kml_now from {os.getpid()}")
    all_kmls = glob.glob(os.path.join(context.tracer_logger.log_path, "kml", "*.kml"))
    if not all_kmls:
        flask.abort(404, "No KMLs exist")
    latest_kml = max(all_kmls, key=os.path.getctime)
    return flask.send_file(
        latest_kml,
        mimetype="application/vnd.google-earth.kml+xml",
        download_name="now.kml",
        as_attachment=True,
    )


@webapp.route("/tracer/kml/<kml>")
@ui_auth.login_required()
def tracer_kmls(kml):
    logger.debug(f"Handling tracer_kmls from {os.getpid()}")
    kmlfile = os.path.join(context.tracer_logger.log_path, "kml", kml)
    if not os.path.exists(kmlfile):
        flask.abort(404)
    return flask.send_file(
        kmlfile,
        mimetype="application/vnd.google-earth.kml+xml",
        download_name=kml,
        as_attachment=True,
    )


@webapp.route("/tracer/kml/historical.kml")
@ui_auth.login_required()
def tracer_kml_historical():
    kml_name = f"historical_{datetime.datetime.now(datetime.UTC).isoformat().split('.')[0]}.kml"
    return flask.Response(
        render_historical_kml(context.tracer_logger.log_path),
        mimetype="application/vnd.google-earth.kml+xml",
        headers={"Content-Disposition": f"attachment;filename={kml_name}"},
    )


def _get_validated_obs_area(observation_area_id: str) -> ObservationArea:
    tx = db.value
    if observation_area_id not in tx.observation_areas:
        flask.abort(404, "Specified observation area not found")
    return tx.observation_areas[observation_area_id]


@webapp.route("/tracer/observation_areas/<observation_area_id>/ui", methods=["GET"])
@ui_auth.login_required(role="admin")
def tracer_observation_area_ui(observation_area_id: str):
    logger.debug(f"Handling tracer_observation_area_ui from {os.getpid()}")
    area = _get_validated_obs_area(observation_area_id)
    v = area.area.volume
    try:
        bbox = geo.make_latlng_rect(v)
        bbox_str = f"{bbox.lo().lat().degrees:6f},{bbox.lo().lng().degrees:6f},{bbox.hi().lat().degrees:6f},{bbox.hi().lng().degrees:6f}"
    except (ValueError, KeyError):
        bbox_str = "[unavailable]"
    if v.altitude_lower:
        alt_lo = f"{v.altitude_lower.value} {v.altitude_lower.units} {v.altitude_lower.reference}"
    else:
        alt_lo = None
    if v.altitude_upper:
        alt_hi = f"{v.altitude_upper.value} {v.altitude_upper.units} {v.altitude_upper.reference}"
    else:
        alt_hi = None
    return flask.render_template(
        "tracer/observation_area_ui.html",
        title=f"Observation area {observation_area_id}",
        area=area,
        bbox_str=bbox_str,
        alt_lo=alt_lo,
        alt_hi=alt_hi,
        now=StringBasedDateTime(arrow.utcnow().datetime),
        username=flask_login.current_user.username,
    )


@webapp.route(
    "/tracer/observation_areas/<observation_area_id>/rid_poll_requests",
    methods=["POST"],
)
@ui_auth.login_required(role="admin")
def tracer_rid_request_poll(observation_area_id: str):
    logger.debug(f"Handling tracer_rid_request_poll from {os.getpid()}")
    area = _get_validated_obs_area(observation_area_id)
    if not area.f3411:
        flask.abort(400, "Specified observation area is not observing F3411 remote ID")
        raise RuntimeError("An exception should have been raised.")
    if not area.area.volume.outline_polygon and not area.area.volume.outline_circle:
        flask.abort(
            400, "Specified observation area does not define its spatial outline"
        )
        raise RuntimeError("An exception should have been raised.")

    rid_client = context.get_client(area.f3411.auth_spec, area.f3411.dss_base_url)
    flights_result = rid.all_flights(
        geo.make_latlng_rect(area.area.volume),
        flask.request.form.get("include_recent_positions", False, type=bool),
        flask.request.form.get("get_details", False, type=bool),
        area.f3411.rid_version,
        rid_client,
        enhanced_details=flask.request.form.get("enhanced_details", False, type=bool),
    )
    log_name = context.tracer_logger.log_new(
        PollFlights(
            observation_area_id=observation_area_id,
            poll=flights_result,
            recorded_at=StringBasedDateTime(arrow.utcnow()),
        )
    )
    return flask.redirect(flask.url_for("tracer_logs", log=log_name))


@webapp.route("/tracer/observation_areas/ui", methods=["GET"])
@ui_auth.login_required()
def tracer_observation_areas_ui():
    return flask.render_template(
        "tracer/observation_areas_ui.html",
        title="Observation Areas UI",
        username=flask_login.current_user.username,
    )
