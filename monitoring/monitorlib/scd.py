from typing import Optional

from uas_standards.astm.f3548.v21.constants import Scope


DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

# API version 0.3.17 is programmatically identical to version 1.0.0, so both these versions can be used interchangeably.
API_1_0_0 = "1.0.0"
API_0_3_17 = API_1_0_0

SCOPE_SC = Scope.StrategicCoordination
SCOPE_CM = Scope.ConstraintManagement
SCOPE_CP = Scope.ConstraintProcessing
SCOPE_CM_SA = Scope.ConformanceMonitoringForSituationalAwareness
SCOPE_AA = Scope.AvailabilityArbitration

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
