import flask
from implicitdict import ImplicitDict
from loguru import logger
from uas_standards.astm.f3411.v22a.api import (
    OPERATIONS,
    OperationID,
    PutIdentificationServiceAreaNotificationParameters,
)
from uas_standards.astm.f3411.v22a.constants import Scope

from monitoring.mock_uss.app import webapp
from monitoring.mock_uss.auth import requires_scope
from monitoring.mock_uss.riddp.database import db
from monitoring.monitorlib.fetch import describe_flask_query
from monitoring.monitorlib.mutate.rid import UpdatedISA


def rid_v22a_operation(op_id: OperationID):
    op = OPERATIONS[op_id]
    path = op.path.replace("{", "<").replace("}", ">")
    return webapp.route("/mock/riddp" + path, methods=[op.verb])


@rid_v22a_operation(OperationID.PostIdentificationServiceArea)
@requires_scope(Scope.ServiceProvider)
def riddp_notify_isa_v22a(id: str):
    try:
        json = flask.request.json
        if json is None:
            raise ValueError("Request did not contain a JSON payload")
        put_params: PutIdentificationServiceAreaNotificationParameters = (
            ImplicitDict.parse(json, PutIdentificationServiceAreaNotificationParameters)
        )
    except ValueError as e:
        msg = f"Unable to parse PutIdentificationServiceAreaNotificationParameters JSON request: {e}"
        return msg, 400

    subscription_ids = [s.subscription_id for s in put_params.subscriptions]
    if subscription_ids:
        with db.transact() as tx:
            updated = False

            for subscription in tx.value.subscriptions:
                if not subscription.upsert_result.subscription:
                    continue
                if subscription.upsert_result.subscription.id in subscription_ids:
                    query = describe_flask_query(flask.request, flask.jsonify(None), 0)
                    subscription.updates.append(UpdatedISA(v22a_query=query))
                    logger.debug(
                        f"Updated subscription {subscription.upsert_result.subscription.id} with ISA {id}"
                    )
                    updated = True
            if not updated:
                logger.warning(
                    f"Update for ISA {id} specified non-existent subscriptions {','.join(subscription_ids)}"
                )

    return (
        flask.jsonify(None),
        204,
    )
