import math
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Literal
from implicitdict import ImplicitDict, StringBasedDateTime

import arrow
import s2sphere
import shapely.geometry

from monitoring.monitorlib.geo import LatLngPoint, Radius
from uas_standards.astm.f3548.v21.api import (
    OperationalIntentState,
    Polygon,
    Volume4D,
    Volume3D,
    Time,
    Altitude,
    Circle,
)

from monitoring.monitorlib import geo


DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

# API version 0.3.17 is programmatically identical to version 1.0.0, so both these versions can be used interchangeably.
API_1_0_0 = "1.0.0"
API_0_3_17 = API_1_0_0

SCOPE_SC = "utm.strategic_coordination"
SCOPE_CM = "utm.constraint_management"
SCOPE_CP = "utm.constraint_processing"
SCOPE_CM_SA = "utm.conformance_monitoring_sa"
SCOPE_AA = "utm.availability_arbitration"

NO_OVN_PHRASES = {"", "Available from USS"}


class Subscription(dict):
    @property
    def valid(self) -> bool:
        if self.version is None:
            return False
        return True

    @property
    def version(self) -> Optional[str]:
        return self.get("version", None)


def op_intent_transition_valid(
    transition_from: Optional[OperationalIntentState],
    transition_to: Optional[OperationalIntentState],
) -> bool:
    valid_states = {
        OperationalIntentState.Accepted,
        OperationalIntentState.Activated,
        OperationalIntentState.Nonconforming,
        OperationalIntentState.Contingent,
    }
    if transition_from is not None and transition_from not in valid_states:
        raise ValueError(
            f"Cannot transition from state {transition_from} as it is an invalid operational intent state"
        )
    if transition_to is not None and transition_to not in valid_states:
        raise ValueError(
            f"Cannot transition to state {transition_to} as it is an invalid operational intent state"
        )

    if transition_from is None:
        return transition_to in {
            OperationalIntentState.Accepted,
            OperationalIntentState.Activated,
        }

    elif transition_from == OperationalIntentState.Accepted:
        return transition_to in {
            None,
            OperationalIntentState.Accepted,
            OperationalIntentState.Activated,
            OperationalIntentState.Nonconforming,
            OperationalIntentState.Contingent,
        }

    elif transition_from == OperationalIntentState.Activated:
        return transition_to in {
            None,
            OperationalIntentState.Activated,
            OperationalIntentState.Nonconforming,
            OperationalIntentState.Contingent,
        }

    elif transition_from == OperationalIntentState.Nonconforming:
        return transition_to in {
            None,
            OperationalIntentState.Nonconforming,
            OperationalIntentState.Activated,
            OperationalIntentState.Contingent,
        }

    elif transition_from == OperationalIntentState.Contingent:
        return transition_to in {None, OperationalIntentState.Contingent}

    else:
        return False
