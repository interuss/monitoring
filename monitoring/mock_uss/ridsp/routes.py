from monitoring.mock_uss import webapp


@webapp.route("/ridsp/status")
def ridsp_status():
    return "Mock RID Service Provider ok"


from . import routes_ridsp_v19
from . import routes_injection
from . import routes_behavior
