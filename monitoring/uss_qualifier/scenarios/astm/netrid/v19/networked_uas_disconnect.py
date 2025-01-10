from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.scenarios.astm.netrid.common.networked_uas_disconnect import (
    NetworkedUASDisconnect as CommonNetworkedUASDisconnect,
)


class NetworkedUASDisconnect(TestScenario, CommonNetworkedUASDisconnect):
    @property
    def _rid_version(self) -> RIDVersion:
        return RIDVersion.f3411_19
