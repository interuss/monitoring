from typing import Dict

from monitoring.uss_qualifier.reports.report import TestSuiteReport
from monitoring.uss_qualifier.resources.definitions import ResourceID
from monitoring.uss_qualifier.resources.interuss.report import TestSuiteReportResource
from monitoring.uss_qualifier.resources.resource import ResourceType
from monitoring.uss_qualifier.scenarios.scenario import (
    GenericTestScenario,
    TestScenario,
)


REPORT_RESOURCE_ID: ResourceID = "report_resource"


class GenericReportEvaluationScenario(GenericTestScenario):

    report: TestSuiteReport

    def __init__(
        self,
        report_resource: TestSuiteReportResource,
    ):
        super().__init__()
        self.report = report_resource.report

    @staticmethod
    def inject_report_resource(
        resources_mapping: Dict[ResourceID, ResourceID],
        resources: Dict[ResourceID, ResourceType],
        report: TestSuiteReport,
    ):
        resources_mapping[REPORT_RESOURCE_ID] = REPORT_RESOURCE_ID
        resources[REPORT_RESOURCE_ID] = TestSuiteReportResource(report)


class ReportEvaluationScenario(GenericReportEvaluationScenario, TestScenario):
    pass
