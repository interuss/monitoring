from implicitdict import ImplicitDict
from typing import List, Optional

from uas_standards.interuss.automated_testing.flight_planning.v1.api import (
    UpsertFlightPlanRequest,
)
from uas_standards.interuss.automated_testing.scd.v1.api import InjectFlightRequest


class MockUssFlightBehavior(ImplicitDict):
    """
    Interface for modifying mock_uss flight sharing behavior with other USSes
    Specify the http method and the fields to modify for those requests

    Eg -
        {"modify_sharing_methods"=["GET", "POST"],
         "modify_fields"={
            "operational_intent_reference": {"state": "Flying"},
            "operational_intent_details": {"priority": -1},
            }
        }
    """

    modify_sharing_methods: List[str]
    """ list of intent sharing http methods GET and POST to be modified"""

    modify_fields: dict
    """dict that specifies the values for the fields to be overriden in the operational_intent while sharing"""


class MockUSSInjectFlightRequest(InjectFlightRequest):
    """InjectFlightRequest sent to mock_uss, which looks for the optional additional fields below."""

    behavior: Optional[MockUssFlightBehavior]


class MockUSSUpsertFlightPlanRequest(UpsertFlightPlanRequest):
    """UpsertFlightPlanRequest sent to mock_uss, which looks for the optional additional fields below."""

    behavior: Optional[MockUssFlightBehavior]
