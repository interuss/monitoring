from monitoring.mock_uss import webapp
from monitoring.mock_uss.riddp.config import KEY_RID_VERSION

from ...monitorlib.rid import RIDVersion

rid_version: RIDVersion = webapp.config[KEY_RID_VERSION]


@webapp.route("/riddp/status")
def riddp_status():
    return "Mock RID Display Provider ok"


if rid_version == RIDVersion.f3411_19:
    from . import routes_riddp_v19
elif rid_version == RIDVersion.f3411_22a:
    from . import routes_riddp_v22a
else:
    raise NotImplementedError(
        f"Mock USS does not yet support RID version {rid_version}"
    )

from . import routes_behavior, routes_observation
