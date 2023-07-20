from typing import Dict

from monitoring.uss_qualifier.reports.report import TestSuiteReport
from monitoring.uss_qualifier.resources.definitions import ResourceID
from monitoring.uss_qualifier.resources.interuss.report import TestSuiteReportResource
from monitoring.uss_qualifier.resources.resource import ResourceType
from monitoring.uss_qualifier.scenarios.scenario import (
    GenericTestScenario,
    TestScenario,
)


# TODO: move to scenarios/interuss ???

REPORT_RESOURCE_ID: ResourceID = "report_resource"


class GenericReportEvaluationScenario(GenericTestScenario):

    report: TestSuiteReport

    def __init__(
        self,
        report_resource: TestSuiteReportResource,
    ):
        super().__init__()
        self.report = report_resource.report
        # TODO: use the kwargs to fetch with RESOURCE_ID ???

    @staticmethod
    def inject_report_resource(
        resources_mapping: Dict[ResourceID, ResourceID],
        resources: Dict[ResourceID, ResourceType],
        report: TestSuiteReport,
    ):
        resources_mapping[REPORT_RESOURCE_ID] = REPORT_RESOURCE_ID
        resources[REPORT_RESOURCE_ID] = TestSuiteReportResource(report)

    # @staticmethod
    # def make_test_suite_action(
    #     scenario_declaration: TestScenarioDeclaration,
    #     resources: Dict[ResourceID, ResourceType],
    #     report: TestSuiteReport,
    # ) -> TestSuiteAction:
    #     scenario_declaration = ImplicitDict.parse(
    #         json.loads(json.dumps(scenario_declaration)),
    #         TestScenarioDeclaration,
    #     )
    #     scenario_declaration.resources = dict(scenario_declaration.resources, **{REPORT_RESOURCE_ID: REPORT_RESOURCE_ID}) # todo inject from resource
    #     action_declaration = ImplicitDict.parse(
    #         dict(
    #             test_scenario=scenario_declaration,
    #         ),
    #         TestSuiteActionDeclaration,
    #     )
    #     action_resources = dict(
    #         resources,
    #         **{REPORT_RESOURCE_ID: TestSuiteReportResource(report)},
    #     )
    #     return TestSuiteAction(
    #         action=action_declaration, resources=action_resources
    #     )


class ReportEvaluationScenario(GenericReportEvaluationScenario, TestScenario):
    pass
