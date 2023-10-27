from monitoring.mock_uss.f3548v21.flight_planning import PlanningError
from monitoring.monitorlib.uspace import problems_with_flight_authorisation
from uas_standards.interuss.automated_testing.scd.v1 import api as scd_api


def validate_request(req_body: scd_api.InjectFlightRequest) -> None:
    """Raise a PlannerError if the request is not valid.

    Args:
        req_body: Information about the requested flight.
    """
    problems = problems_with_flight_authorisation(req_body.flight_authorisation)
    if problems:
        raise PlanningError(", ".join(problems))
