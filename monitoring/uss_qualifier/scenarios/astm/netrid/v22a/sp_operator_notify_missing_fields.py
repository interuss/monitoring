from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.scenarios.astm.netrid.common.sp_operator_notify_missing_fields import (
    SpOperatorNotifyMissingFields as CommonSpOperatorNotifyMissingFields,
)


class SpOperatorNotifyMissingFields(TestScenario, CommonSpOperatorNotifyMissingFields):
    @property
    def _rid_version(self) -> RIDVersion:
        return RIDVersion.f3411_22a
