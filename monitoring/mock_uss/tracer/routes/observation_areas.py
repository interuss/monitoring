import os
import uuid
from datetime import datetime
from typing import Tuple, List

import flask
import s2sphere
from loguru import logger

from implicitdict import ImplicitDict, StringBasedDateTime
from monitoring.mock_uss import webapp
from monitoring.mock_uss.tracer import context
from monitoring.mock_uss.tracer.database import db
from monitoring.mock_uss.tracer.observation_area_operations import (
    redact_observation_area,
    delete_observation_area,
    create_observation_area,
)
from monitoring.mock_uss.tracer.observation_areas import (
    ListObservationAreasResponse,
    PutObservationAreaRequest,
    ObservationAreaResponse,
    ObservationArea,
    ImportObservationAreasRequest,
    F3411ObservationArea,
)
from monitoring.mock_uss.tracer.tracer_poll import TASK_POLL_OBSERVATION_AREAS
from monitoring.monitorlib import fetch
import monitoring.monitorlib.fetch.rid
from monitoring.monitorlib.geo import Volume3D
from monitoring.monitorlib.geotemporal import Volume4D


@webapp.route("/tracer/observation_areas", methods=["GET"])
def tracer_list_observation_areas() -> Tuple[str, int]:
    with db as tx:
        result = ListObservationAreasResponse(
            areas=[redact_observation_area(a) for a in tx.observation_areas.values()]
        )
    return flask.jsonify(result)


@webapp.route("/tracer/observation_areas/<area_id>", methods=["PUT"])
def tracer_upsert_observation_area(area_id: str) -> Tuple[str, int]:
    try:
        req_body = flask.request.json
        if req_body is None:
            raise ValueError("Request did not contain a JSON payload")
        import json

        request: PutObservationAreaRequest = ImplicitDict.parse(
            req_body, PutObservationAreaRequest
        )
    except ValueError as e:
        msg = "Upsert observation area for tracer unable to parse JSON: {}".format(e)
        return msg, 400

    with db as tx:
        # Determine if this observation area triggers the need to start polling
        if tx.observation_areas:
            poll_interval = tx.polling_interval.timedelta
            for a in tx.observation_areas.values():
                if a.polls:
                    poll_interval = None
                    break
        else:
            poll_interval = (
                tx.polling_interval.timedelta if request.area.polls else None
            )

        if area_id in tx.observation_areas:
            # Request is to mutate an existing observation area, so we'll first just delete the existing area
            delete_observation_area(tx.observation_areas[area_id])
        created = create_observation_area(area_id, request.area)
        tx.observation_areas[area_id] = created

    if poll_interval is not None:
        webapp.set_task_period(TASK_POLL_OBSERVATION_AREAS, poll_interval)
    return flask.jsonify(ObservationAreaResponse(area=redact_observation_area(created)))


@webapp.route("/tracer/observation_areas/<area_id>", methods=["DELETE"])
def tracer_delete_observation_area(area_id: str) -> Tuple[str, int]:
    with db as tx:
        if area_id not in tx.observation_areas:
            return "Specified observation area not in system", 404
        area = tx.observation_areas.pop(area_id)
        area = delete_observation_area(area)
        remaining_polling_areas = sum(
            1 if a.polls else 0 for a in tx.observation_areas.values()
        )

    if not remaining_polling_areas:
        webapp.set_task_period(TASK_POLL_OBSERVATION_AREAS, None)
    return flask.jsonify(ObservationAreaResponse(area=redact_observation_area(area)))


@webapp.route("/tracer/observation_areas/import_requests", methods=["POST"])
def tracer_import_observation_areas() -> Tuple[str, int]:
    try:
        req_body = flask.request.json
        if req_body is None:
            raise ValueError("Request did not contain a JSON payload")
        import json

        request: ImportObservationAreasRequest = ImplicitDict.parse(
            req_body, ImportObservationAreasRequest
        )
    except ValueError as e:
        msg = "Import observation area for tracer unable to parse JSON: {}".format(e)
        return msg, 400

    auth_spec = context.resolve_auth_spec(None)

    f3411_obs_areas = []
    if request.f3411 is not None:
        if request.area.volume.outline_circle:
            raise NotImplementedError(
                "Import observation areas does not yet support circular areas for F3411"
            )
        elif request.area.volume.outline_polygon:
            points = [
                s2sphere.LatLng.from_degrees(p.lat, p.lng)
                for p in request.area.volume.outline_polygon.vertices
            ]
        else:
            raise NotImplementedError(
                "Import observation areas requires a circle or polygon outline"
            )
        dss_base_url = context.resolve_rid_dss_base_url("", request.f3411)
        rid_client = context.get_client(auth_spec, dss_base_url)
        rid_subscriptions = fetch.rid.subscriptions(
            area=points,
            rid_version=request.f3411,
            session=rid_client,
        )
        if not rid_subscriptions.success:
            context.tracer_logger.log_new(
                "import_observation_areas_rid_error", rid_subscriptions
            )
            return (
                f"Could not retrieve F3411 subscriptions (code {rid_subscriptions.status_code})",
                412,
            )
        for rid_subscription in rid_subscriptions.subscriptions.values():
            obs_area = ObservationArea(
                id=str(uuid.uuid4()),
                area=Volume4D(
                    volume=Volume3D(),
                    time_start=StringBasedDateTime(rid_subscription.time_start),
                    time_end=StringBasedDateTime(rid_subscription.time_end),
                ),
                f3411=F3411ObservationArea(
                    auth_spec=auth_spec,
                    dss_base_url=dss_base_url,
                    rid_version=request.f3411,
                    poll=False,
                    subscription_id=rid_subscription.id,
                ),
            )
            f3411_obs_areas.append(obs_area)

    f3548_obs_areas = []
    if request.f3548:
        # TODO: Implement
        raise NotImplementedError(
            "Import of F3548 subscriptions into observation areas is not yet implemented"
        )

    with db as tx:
        new_obs_areas = []

        f3411_subscription_ids = {
            a.f3411.subscription_id for a in tx.observation_areas.values() if a.f3411
        }
        new_obs_areas.extend(
            a
            for a in f3411_obs_areas
            if a.f3411.subscription_id not in f3411_subscription_ids
        )

        f3548_subscription_ids = {
            a.f3548.subscription_id for a in tx.observation_areas.values() if a.f3548
        }
        new_obs_areas.extend(
            a
            for a in f3548_obs_areas
            if a.f3548.subscription_id not in f3548_subscription_ids
        )

        for obs_area in new_obs_areas:
            tx.observation_areas[obs_area.id] = obs_area

    return flask.jsonify(
        ListObservationAreasResponse(
            areas=[redact_observation_area(a) for a in new_obs_areas]
        )
    )


@webapp.shutdown_task("observation areas cleanup")
def _shutdown():
    logger.info(
        f"Cleaning up observation areas from PID {os.getpid()} at {datetime.utcnow()}..."
    )

    with db as tx:
        observation_areas: List[ObservationArea] = [v for _, v in tx.observation_areas]
        tx.observation_areas.clear()

    for area in observation_areas:
        delete_observation_area(area)

    logger.info("Observation areas cleanup complete.")

    context.tracer_logger.log_new(
        "tracer_stop",
        {
            "timestamp": datetime.utcnow(),
        },
    )
