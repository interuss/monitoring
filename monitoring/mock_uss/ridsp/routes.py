from monitoring.mock_uss import webapp
from monitoring.mock_uss.riddp.config import KEY_RID_VERSION
from monitoring.monitorlib.rid import RIDVersion


rid_version: RIDVersion = webapp.config[KEY_RID_VERSION]


@webapp.route("/ridsp/status")
def ridsp_status():
    return f"Mock RID Service Provider ok; RID version {rid_version}"


if rid_version == RIDVersion.f3411_19:
    from . import routes_ridsp_v19
elif rid_version == RIDVersion.f3411_22a:
    from . import routes_ridsp_v22a
else:
    raise NotImplementedError(
        f"Mock USS does not yet support RID version {rid_version}"
    )

from . import routes_injection
from . import routes_behavior
