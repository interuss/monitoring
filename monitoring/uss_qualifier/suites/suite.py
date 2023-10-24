from __future__ import annotations

import os
from datetime import datetime
import json
from typing import Dict, List, Optional, Union, Callable, Iterator

import arrow

from implicitdict import StringBasedDateTime, ImplicitDict
from loguru import logger
import yaml

from monitoring.monitorlib.inspection import fullname
from monitoring.monitorlib.versioning import repo_url_of
from monitoring.uss_qualifier.action_generators.action_generator import (
    ActionGeneratorType,
    ActionGenerator,
)
from monitoring.uss_qualifier.fileio import resolve_filename
from monitoring.uss_qualifier.reports.capabilities import (
    evaluate_condition_for_test_suite,
)
from monitoring.uss_qualifier.scenarios.interuss.evaluation_scenario import (
    ReportEvaluationScenario,
)
from monitoring.uss_qualifier.reports.report import (
    ActionGeneratorReport,
    TestScenarioReport,
    FailedCheck,
    TestSuiteReport,
    TestSuiteActionReport,
    ParticipantCapabilityEvaluationReport,
    SkippedActionReport,
)
from monitoring.uss_qualifier.resources.definitions import ResourceID
from monitoring.uss_qualifier.resources.resource import (
    ResourceType,
    make_child_resources,
    MissingResourceError,
    create_resources,
)
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
    ScenarioCannotContinueError,
    TestRunCannotContinueError,
)
from monitoring.uss_qualifier.suites.definitions import (
    TestSuiteActionDeclaration,
    TestSuiteDefinition,
    ReactionToFailure,
    ActionType,
    TestSuiteDeclaration,
)


def _print_failed_check(failed_check: FailedCheck) -> None:
    yaml_lines = yaml.dump(json.loads(json.dumps(failed_check))).split("\n")
    logger.warning(
        "New failed check:\n{}", "\n".join("  " + line for line in yaml_lines)
    )


class TestSuiteAction(object):
    declaration: TestSuiteActionDeclaration
    test_scenario: Optional[TestScenario] = None
    test_suite: Optional[TestSuite] = None
    action_generator: Optional[ActionGeneratorType] = None

    def __init__(
        self,
        action: TestSuiteActionDeclaration,
        resources: Dict[ResourceID, ResourceType],
    ):
        self.declaration = action
        resources_for_child = make_child_resources(
            resources,
            action.get_resource_links(),
            f"Test suite action to run {action.get_action_type()} {action.get_child_type()}",
        )

        action_type = action.get_action_type()
        if action_type == ActionType.TestScenario:
            self.test_scenario = TestScenario.make_test_scenario(
                declaration=action.test_scenario, resource_pool=resources_for_child
            )
        elif action_type == ActionType.TestSuite:
            self.test_suite = TestSuite(
                declaration=action.test_suite,
                resources=resources,
            )
        elif action_type == ActionType.ActionGenerator:
            self.action_generator = ActionGenerator.make_from_definition(
                definition=action.action_generator, resources=resources_for_child
            )
        else:
            ActionType.raise_invalid_action_declaration()

    def run(self) -> TestSuiteActionReport:
        if self.test_scenario:
            return TestSuiteActionReport(test_scenario=self._run_test_scenario())
        elif self.test_suite:
            return TestSuiteActionReport(test_suite=self._run_test_suite())
        elif self.action_generator:
            return TestSuiteActionReport(action_generator=self._run_action_generator())

    def _run_test_scenario(self) -> TestScenarioReport:
        scenario = self.test_scenario
        logger.info(f'Running "{scenario.documentation.name}" scenario...')
        scenario.on_failed_check = _print_failed_check
        try:
            try:
                scenario.run()
            except (ScenarioCannotContinueError, TestRunCannotContinueError):
                pass
            scenario.go_to_cleanup()
            try:
                scenario.cleanup()
            except (ScenarioCannotContinueError, TestRunCannotContinueError):
                scenario.ensure_cleanup_ended()
        except KeyboardInterrupt:
            raise
        except Exception as e:
            scenario.record_execution_error(e)
        report = scenario.get_report()
        if report.successful:
            logger.info(f'SUCCESS for "{scenario.documentation.name}" scenario')
        else:
            if "execution_error" in report:
                lines = report.execution_error.stacktrace.split("\n")
                logger.error(
                    "Execution error:\n{}", "\n".join("  " + line for line in lines)
                )
            logger.warning(f'FAILURE for "{scenario.documentation.name}" scenario')
        return report

    def _run_test_suite(self) -> TestSuiteReport:
        logger.info(f"Beginning test suite {self.test_suite.definition.name}...")
        report = self.test_suite.run()
        logger.info(f"Completed test suite {self.test_suite.definition.name}")
        return report

    def _run_action_generator(self) -> ActionGeneratorReport:
        report = ActionGeneratorReport(
            actions=[],
            generator_type=self.action_generator.definition.generator_type,
            start_time=StringBasedDateTime(arrow.utcnow()),
        )

        _run_actions(self.action_generator.actions(), report)

        return report


class TestSuite(object):
    declaration: TestSuiteDeclaration
    definition: TestSuiteDefinition
    documentation_url: str
    local_resources: Dict[ResourceID, ResourceType]
    actions: List[Union[TestSuiteAction, SkippedActionReport]]

    def __init__(
        self,
        declaration: TestSuiteDeclaration,
        resources: Dict[ResourceID, ResourceType],
    ):
        # Determine the suite's documentation URL
        if "suite_type" in declaration and declaration.suite_type:
            suite_yaml_path = resolve_filename(declaration.suite_type)
            if suite_yaml_path.lower().startswith(
                "http://"
            ) or suite_yaml_path.lower().startswith("https://"):
                self.documentation_url = suite_yaml_path
            else:
                self.documentation_url = repo_url_of(
                    os.path.splitext(suite_yaml_path)[0] + ".md"
                )
        elif "suite_definition" in declaration and declaration.suite_definition:
            # TODO: Accept information about the declaration origin in order to populate the URL in this case
            self.documentation_url = ""
        else:
            raise ValueError(
                "Unrecognized declaration type (neither suite_type nor suite_definition were defined)"
            )

        self.declaration = declaration
        self.definition = TestSuiteDefinition.load_from_declaration(declaration)
        if "resources" in declaration and declaration.resources:
            self.local_resources = {
                local_resource_id: resources[parent_resource_id]
                for local_resource_id, parent_resource_id in declaration.resources.items()
            }
        else:
            self.local_resources = {}
        if "local_resources" in self.definition and self.definition.local_resources:
            local_resources = create_resources(self.definition.local_resources)
            for local_resource_id, resource in local_resources.items():
                self.local_resources[local_resource_id] = resource

        for resource_id, resource_type in self.definition.resources.items():
            is_optional = resource_type.endswith("?")
            if is_optional:
                resource_type = resource_type[:-1]
            if not is_optional and resource_id not in self.local_resources:
                raise MissingResourceError(
                    f'Test suite "{self.definition.name}" is missing resource {resource_id} ({resource_type})',
                    resource_id,
                )
            if resource_id in self.local_resources and not self.local_resources[
                resource_id
            ].is_type(resource_type):
                raise ValueError(
                    f'Test suite "{self.definition.name}" expected resource {resource_id} to be {resource_type}, but instead it was provided {fullname(self.local_resources[resource_id].__class__)}'
                )
        actions: List[Union[TestSuiteAction, SkippedActionReport]] = []
        for a, action_dec in enumerate(self.definition.actions):
            try:
                actions.append(
                    TestSuiteAction(action=action_dec, resources=self.local_resources)
                )
            except MissingResourceError as e:
                logger.warning(
                    f"Skipping action {a} ({action_dec.get_action_type()} {action_dec.get_child_type()}) because {str(e)}"
                )
                actions.append(
                    SkippedActionReport(
                        timestamp=StringBasedDateTime(arrow.utcnow().datetime),
                        reason=str(e),
                        action_declaration_index=a,
                        declaration=action_dec,
                    )
                )
        self.actions = actions

    def _make_report_evaluation_action(
        self, report: TestSuiteReport
    ) -> TestSuiteAction:
        """Create the action wrapping the ReportEvaluationScenario and inject the required resources."""

        ReportEvaluationScenario.inject_report_resource(
            self.definition.report_evaluation_scenario.resources,
            self.local_resources,
            report,
        )
        action_declaration = ImplicitDict.parse(
            dict(
                test_scenario=self.definition.report_evaluation_scenario,
            ),
            TestSuiteActionDeclaration,
        )
        action = TestSuiteAction(
            action=action_declaration, resources=self.local_resources
        )
        if not issubclass(action.test_scenario.__class__, ReportEvaluationScenario):
            raise ValueError(
                f"Scenario type {action.test_scenario.__class__} is not a subclass of the ReportEvaluationScenario base class"
            )
        return action

    def run(self) -> TestSuiteReport:
        report = TestSuiteReport(
            name=self.definition.name,
            suite_type=self.declaration.type_name,
            documentation_url=self.documentation_url,
            start_time=StringBasedDateTime(datetime.utcnow()),
            actions=[],
            capability_evaluations=[],
        )

        def actions() -> Iterator[Union[TestSuiteAction, SkippedActionReport]]:
            for a in self.actions:
                yield a
            # Execute report evaluation scenario as last action if specified, otherwise break loop
            if self.definition.has_field_with_value("report_evaluation_scenario"):
                yield self._make_report_evaluation_action(report)

        _run_actions(actions(), report)

        # Evaluate participants' capabilities
        if (
            "participant_verifiable_capabilities" in self.definition
            and self.definition.participant_verifiable_capabilities
        ):
            all_participants = report.all_participants()
            for capability in self.definition.participant_verifiable_capabilities:
                for participant_id in all_participants:
                    cond_eval_report = evaluate_condition_for_test_suite(
                        capability.verification_condition, participant_id, report
                    )
                    report.capability_evaluations.append(
                        ParticipantCapabilityEvaluationReport(
                            capability_id=capability.id,
                            participant_id=participant_id,
                            verified=cond_eval_report.condition_satisfied,
                            condition_evaluation=cond_eval_report,
                        )
                    )
                    if cond_eval_report.condition_satisfied:
                        logger.info(
                            "Test suite {} verified {} capability '{}' for {}",
                            self.declaration.type_name,
                            capability.id,
                            capability.name,
                            participant_id,
                        )

        return report


def _run_actions(
    actions: Iterator[Union[TestSuiteAction, SkippedActionReport]],
    report: Union[TestSuiteReport, ActionGeneratorReport],
) -> None:
    success = True
    for a, action in enumerate(actions):
        if isinstance(action, SkippedActionReport):
            action_report = TestSuiteActionReport(skipped_action=action)
        else:
            action_report = action.run()
        report.actions.append(action_report)
        if action_report.has_critical_problem():
            success = False
            break
        if not action_report.successful():
            success = False
            if action.declaration.on_failure == ReactionToFailure.Abort:
                break
            elif action.declaration.on_failure == ReactionToFailure.Continue:
                continue
            else:
                raise ValueError(
                    f"Action {a} indicated an unrecognized reaction to failure: {str(action.declaration.on_failure)}"
                )
    report.successful = success
    report.end_time = StringBasedDateTime(datetime.utcnow())
