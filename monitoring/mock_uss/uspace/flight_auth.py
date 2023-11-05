from monitoring.mock_uss.f3548v21.flight_planning import PlanningError
from monitoring.monitorlib.clients.flight_planning.flight_info import FlightInfo
from monitoring.monitorlib.uspace import problems_with_flight_authorisation


def validate_request(flight_info: FlightInfo) -> None:
    """Raise a PlannerError if the request is not valid.

    Args:
        flight_info: Information about the requested flight.
    """
    problems = problems_with_flight_authorisation(
        flight_info.uspace_flight_authorisation
    )
    if problems:
        raise PlanningError(", ".join(problems))
