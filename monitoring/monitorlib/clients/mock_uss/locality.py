from implicitdict import ImplicitDict

from monitoring.monitorlib.locality import LocalityCode


class PutLocalityRequest(ImplicitDict):
    """API object to request a change in locality"""

    locality_code: LocalityCode


class GetLocalityResponse(ImplicitDict):
    """API object defining a response indicating locality"""

    locality_code: LocalityCode
