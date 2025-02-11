from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.scenarios.astm.netrid.common.networked_uas_disconnect import (
    NetworkedUASDisconnect as CommonNetworkedUASDisconnect,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class NetworkedUASDisconnect(TestScenario, CommonNetworkedUASDisconnect):
    @property
    def _rid_version(self) -> RIDVersion:
        return RIDVersion.f3411_22a
