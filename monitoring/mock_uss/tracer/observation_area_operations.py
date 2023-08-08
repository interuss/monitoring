from implicitdict import ImplicitDict
from monitoring.mock_uss.tracer import context
from monitoring.mock_uss.tracer.observation_areas import (
    ObservationArea,
    ObservationAreaRequest,
    F3411ObservationArea,
    F3548ObservationArea,
    ObservationAreaID,
)
from monitoring.mock_uss.tracer.subscriptions import (
    subscribe_rid,
    subscribe_scd,
    unsubscribe_rid,
    unsubscribe_scd,
)


def redact_observation_area(original: ObservationArea) -> ObservationArea:
    # TODO: redact less information about auth spec
    redacted: ObservationArea = ImplicitDict.parse(original, ObservationArea)
    if redacted.f3411:
        redacted.f3411.auth_spec = "REDACTED"
    if redacted.f3548:
        redacted.f3548.auth_spec = "REDACTED"
    return redacted


def create_observation_area(
    area_id: ObservationAreaID, request: ObservationAreaRequest
) -> ObservationArea:
    if request.f3411 is not None:
        auth_spec = context.resolve_auth_spec(request.f3411.auth_spec)
        dss_base_url = context.resolve_rid_dss_base_url(
            request.f3411.dss_base_url, request.f3411.rid_version
        )
        rid_client = context.get_client(auth_spec, dss_base_url)
        if request.f3411.subscribe:
            subscription_id = subscribe_rid(
                area_id=area_id,
                area=request.area,
                rid_version=request.f3411.rid_version,
                rid_client=rid_client,
            )
        else:
            subscription_id = None
        f3411 = F3411ObservationArea(
            auth_spec=auth_spec,
            dss_base_url=dss_base_url,
            rid_version=request.f3411.rid_version,
            poll=request.f3411.poll,
            subscription_id=subscription_id,
        )
    else:
        f3411 = None

    if request.f3548 is not None:
        auth_spec = context.resolve_auth_spec(request.f3548.auth_spec)
        dss_base_url = context.resolve_scd_dss_base_url(request.f3548.dss_base_url)
        scd_client = context.get_client(auth_spec, dss_base_url)
        if request.f3548.subscribe:
            subscription_id = subscribe_scd(
                area_id=area_id,
                area=request.area,
                op_intents=request.f3548.monitor_op_intents,
                constraints=request.f3548.monitor_constraints,
                scd_client=scd_client,
            )
        else:
            subscription_id = None
        f3548 = F3548ObservationArea(
            auth_spec=auth_spec,
            dss_base_url=dss_base_url,
            monitor_op_intents=request.f3548.monitor_op_intents,
            monitor_constraints=request.f3548.monitor_constraints,
            poll=request.f3548.poll,
            subscription_id=subscription_id,
        )
    else:
        f3548 = None

    return ObservationArea(
        id=area_id,
        area=request.area,
        f3411=f3411,
        f3548=f3548,
    )


def delete_observation_area(area: ObservationArea) -> ObservationArea:
    if area.f3411 is not None:
        rid_client = context.get_client(area.f3411.auth_spec, area.f3411.dss_base_url)
        if area.f3411.subscription_id:
            unsubscribe_rid(
                subscription_id=area.f3411.subscription_id,
                rid_version=area.f3411.rid_version,
                rid_client=rid_client,
            )

    if area.f3548 is not None:
        scd_client = context.get_client(area.f3548.auth_spec, area.f3548.dss_base_url)
        if area.f3548.subscription_id:
            unsubscribe_scd(
                subscription_id=area.f3548.subscription_id, scd_client=scd_client
            )

    return area
