from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.scenarios.astm.netrid.common.sp_notification_behavior import (
    ServiceProviderNotificationBehavior as CommonServiceProviderNotificationBehavior,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class ServiceProviderNotificationBehavior(
    TestScenario, CommonServiceProviderNotificationBehavior
):
    @property
    def _rid_version(self) -> RIDVersion:
        return RIDVersion.f3411_22a
