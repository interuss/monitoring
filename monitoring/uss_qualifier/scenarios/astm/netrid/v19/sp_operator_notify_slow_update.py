from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.scenarios.astm.netrid.common.sp_operator_notify_slow_update import (
    ServiceProviderNotifiesSlowUpdates as CommonServiceProviderNotifiesSlowUpdates,
)


class ServiceProviderNotifiesSlowUpdates(
    TestScenario, CommonServiceProviderNotifiesSlowUpdates
):
    @property
    def _rid_version(self) -> RIDVersion:
        return RIDVersion.f3411_19
