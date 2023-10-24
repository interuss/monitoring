from implicitdict import ImplicitDict
from typing import List, Optional
from uas_standards.interuss.automated_testing.scd.v1.api import InjectFlightRequest


class MockUssFlightBehavior(ImplicitDict):
    """
    Interface for modifying mock_uss flight sharing behavior with other USSes
    modify_sharing_methods: list of intent sharing methods GET and POST that are to be modified
    modify_fields: dict that specifies the values that need to be overriden
     in the opertional_intent while sharing
    Eg -

        {"modify_sharing_methods"=["GET", "POST"],
         "modify_fields"={
            "operational_intent_reference": {"state": "Flying"},
            "operational_intent_details": {"priority": -1},
            }
        }
    """
    modify_sharing_methods: List[str]
    modify_fields: dict


class AddlFieldsInjectFlightRequest(InjectFlightRequest):
    """InjectFlightRequest with additional_fields"""
    additional_fields: Optional[dict]
