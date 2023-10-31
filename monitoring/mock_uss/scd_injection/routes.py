from monitoring.mock_uss import webapp


@webapp.route("/scdsc/status")
def scdsc_status():
    return "scd flight injection API ok"
