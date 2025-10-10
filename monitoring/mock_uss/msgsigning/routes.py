from monitoring.mock_uss.app import webapp

from . import routes_msgsigning as routes_msgsigning


@webapp.route("/mock/msgsigning/status")
def msgsigning_status():
    return "Mock Message Signing Service Provider ok"
