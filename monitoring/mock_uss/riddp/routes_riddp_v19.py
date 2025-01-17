import flask
from implicitdict import ImplicitDict
from uas_standards.astm.f3411.v19.api import (
    OperationID,
    OPERATIONS,
    PutIdentificationServiceAreaNotificationParameters,
)
from uas_standards.astm.f3411.v19.constants import (
    Scope,
)

from monitoring.mock_uss import webapp
from monitoring.mock_uss.auth import requires_scope


def rid_v19_operation(op_id: OperationID):
    op = OPERATIONS[op_id]
    path = op.path.replace("{", "<").replace("}", ">")
    return webapp.route("/mock/riddp" + path, methods=[op.verb])


@rid_v19_operation(OperationID.PostIdentificationServiceArea)
@requires_scope(Scope.Write)
def ridsp_notify_isa_v19(id: str):
    try:
        json = flask.request.json
        if json is None:
            raise ValueError("Request did not contain a JSON payload")
        ImplicitDict.parse(json, PutIdentificationServiceAreaNotificationParameters)
    except ValueError as e:
        msg = "Unable to parse PutIdentificationServiceAreaNotificationParameters JSON request: {}".format(
            e
        )
        return msg, 400

    return (
        flask.jsonify(None),
        204,
    )
