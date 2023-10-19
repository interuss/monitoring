from implicitdict import ImplicitDict
from typing import List, Optional
from uas_standards.interuss.automated_testing.scd.v1.api import InjectFlightRequest


class MockUssFlightBehavior(ImplicitDict):
    modify_sharing_methods: List[str]
    modify_fields: dict


class MockUssInjectFlightRequest(InjectFlightRequest):
    mock_uss_flight_behavior: Optional[MockUssFlightBehavior]
