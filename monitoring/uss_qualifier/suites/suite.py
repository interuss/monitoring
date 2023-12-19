from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
import json
import re
from typing import Dict, List, Optional, Union, Iterator

import arrow

from implicitdict import StringBasedDateTime
from loguru import logger
import yaml

from monitoring.monitorlib.dicts import JSONAddress
from monitoring.monitorlib.fetch import Query
from monitoring.monitorlib.inspection import fullname
from monitoring.monitorlib.versioning import repo_url_of
from monitoring.uss_qualifier.action_generators.action_generator import (
    ActionGeneratorType,
    ActionGenerator,
    action_generator_type_from_name,
)
from monitoring.uss_qualifier.configurations.configuration import (
    ExecutionConfiguration,
    TestSuiteActionSelectionCondition,
)
from monitoring.uss_qualifier.fileio import resolve_filename
from monitoring.uss_qualifier.reports.capabilities import (
    evaluate_condition_for_test_suite,
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

    def get_name(self) -> str:
        if self.test_suite:
            return self.test_suite.definition.name
        elif self.action_generator:
            return self.action_generator.get_name()
        elif self.test_scenario:
            return self.test_scenario.documentation.name
        else:
            raise ValueError(
                "TestSuiteAction as not a suite, action generator, nor scenario"
            )

    def run(self, context: ExecutionContext) -> TestSuiteActionReport:
        context.begin_action(self)
        skip_report = context.evaluate_skip()
        if skip_report:
            logger.warning(
                f"Skipping {self.declaration.get_action_type()} '{self.get_name()}' because: {skip_report.reason}"
            )
            report = TestSuiteActionReport(skipped_action=skip_report)
        else:
            if self.test_scenario:
                report = TestSuiteActionReport(
                    test_scenario=self._run_test_scenario(context)
                )
            elif self.test_suite:
                report = TestSuiteActionReport(test_suite=self._run_test_suite(context))
            elif self.action_generator:
                report = TestSuiteActionReport(
                    action_generator=self._run_action_generator(context)
                )
            else:
                raise ValueError(
                    "TestSuiteAction was not a test scenario, test suite, nor action generator"
                )
        context.end_action(self, report)
        return report

    def _run_test_scenario(self, context: ExecutionContext) -> TestScenarioReport:
        scenario = self.test_scenario

        logger.info(f'Running "{scenario.documentation.name}" scenario...')
        scenario.on_failed_check = _print_failed_check
        try:
            try:
                scenario.run(context)
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

    def _run_test_suite(self, context: ExecutionContext) -> TestSuiteReport:
        logger.info(f"Beginning test suite {self.test_suite.definition.name}...")
        report = self.test_suite.run(context)
        logger.info(f"Completed test suite {self.test_suite.definition.name}")
        return report

    def _run_action_generator(self, context: ExecutionContext) -> ActionGeneratorReport:
        report = ActionGeneratorReport(
            actions=[],
            generator_type=self.action_generator.definition.generator_type,
            start_time=StringBasedDateTime(arrow.utcnow()),
        )

        _run_actions(self.action_generator.actions(), context, report)

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
            if "suite_type" in declaration and declaration.suite_type:
                subject = declaration.suite_type
            else:
                subject = "<custom definition>"
            self.local_resources = make_child_resources(
                resources, declaration.resources, f"Test suite {subject}"
            )
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
                        declaration=action_dec,
                    )
                )
        self.actions = actions

    def run(self, context: ExecutionContext) -> TestSuiteReport:
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

        _run_actions(actions(), context, report)

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
    context: ExecutionContext,
    report: Union[TestSuiteReport, ActionGeneratorReport],
) -> None:
    success = True
    for a, action in enumerate(actions):
        if isinstance(action, SkippedActionReport):
            action_report = TestSuiteActionReport(skipped_action=action)
        else:
            action_report = action.run(context)
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


@dataclass
class ActionStackFrame(object):
    action: TestSuiteAction
    parent: Optional[ActionStackFrame]
    children: List[ActionStackFrame]
    report: Optional[TestSuiteActionReport] = None

    def address(self) -> JSONAddress:
        if self.action.test_scenario is not None:
            addr = "test_scenario"
        elif self.action.test_suite is not None:
            addr = "test_suite"
        elif self.action.action_generator is not None:
            addr = "action_generator"
        else:
            raise ValueError(
                "TestSuiteAction was not a scenario, suite, or action generator"
            )

        if self.parent is None:
            return addr

        index = -1
        for a, child in enumerate(self.parent.children):
            if child is self:
                index = a
                break
        if index == -1:
            raise RuntimeError(
                "ActionStackFrame was not listed as a child of its parent"
            )
        return f"{self.parent.address()}.actions[{index}].{addr}"


class ExecutionContext(object):
    start_time: datetime
    config: Optional[ExecutionConfiguration]
    top_frame: Optional[ActionStackFrame]
    current_frame: Optional[ActionStackFrame]

    def __init__(self, config: Optional[ExecutionConfiguration]):
        self.config = config
        self.top_frame = None
        self.current_frame = None
        self.start_time = arrow.utcnow().datetime

    def sibling_queries(self) -> Iterator[Query]:
        if self.current_frame.parent is None:
            return
        for child in self.current_frame.parent.children:
            if child.report is not None:
                for q in child.report.queries():
                    yield q

    @property
    def stop_fast(self) -> bool:
        if (
            self.config is not None
            and "stop_fast" in self.config
            and self.config.stop_fast is not None
        ):
            return self.config.stop_fast
        return False

    def _compute_n_of(
        self, target: TestSuiteAction, condition: TestSuiteActionSelectionCondition
    ) -> int:
        n = 0
        queue = [self.top_frame]
        while queue:
            frame = queue.pop(0)
            if self._is_selected_by(frame, condition):
                n += 1
            if frame.action is target:
                return n
            for c, child in enumerate(frame.children):
                queue.insert(c, child)
        raise RuntimeError(
            f"Could not find target action '{target.get_name()}' anywhere in ExecutionContext"
        )

    def _ancestor_selected_by(
        self,
        frame: Optional[ActionStackFrame],
        of_generation: Optional[int],
        which: List[TestSuiteActionSelectionCondition],
    ) -> bool:
        if frame is None:
            return False

        if of_generation is not None:
            check_self = of_generation == 0
            of_generation -= 1
        else:
            check_self = True

        if check_self:
            if all(self._is_selected_by(frame, c) for c in which):
                return True

        return self._ancestor_selected_by(frame.parent, of_generation, which)

    def _is_selected_by(
        self, frame: ActionStackFrame, f: TestSuiteActionSelectionCondition
    ) -> bool:
        action = frame.action
        result = False

        if "is_action_generator" in f and f.is_action_generator is not None:
            if action.action_generator:
                if (
                    "types" in f.is_action_generator
                    and f.is_action_generator.types is not None
                ):
                    if not any(
                        type(action.action_generator)
                        is action_generator_type_from_name(t)
                        for t in f.is_action_generator.types
                    ):
                        return False
                result = True
            else:
                return False

        if "is_test_suite" in f and f.is_test_suite is not None:
            if action.test_suite:
                if "types" in f.is_test_suite and f.is_test_suite.types is not None:
                    if (
                        action.test_suite.declaration.suite_type
                        not in f.is_test_suite.types
                    ):
                        return False
                result = True
            else:
                return False

        if "is_test_scenario" in f and f.is_test_scenario is not None:
            if action.test_scenario:
                if (
                    "types" in f.is_test_scenario
                    and f.is_test_scenario.types is not None
                ):
                    if (
                        action.test_scenario.declaration.scenario_type
                        not in f.is_test_scenario.types
                    ):
                        return False
                result = True
            else:
                return False

        if "regex_matches_name" in f and f.regex_matches_name is not None:
            if re.search(f.regex_matches_name, action.get_name()) is None:
                return False
            result = True

        if "defined_at" in f and f.defined_at is not None:
            if frame.address() not in f.defined_at:
                return False
            result = True

        if "nth_instance" in f and f.nth_instance is not None:
            if self._is_selected_by(frame, f.nth_instance.where_action):
                n = self._compute_n_of(frame.action, f.nth_instance.where_action)
                if not any(r.includes(n) for r in f.nth_instance.n):
                    return False
                result = True
            else:
                return False

        if "has_ancestor" in f and f.has_ancestor is not None:
            if (
                "of_generation" in f.has_ancestor
                and f.has_ancestor.of_generation is not None
            ):
                of_generation = f.has_ancestor.of_generation - 1
            else:
                of_generation = None
            if not self._ancestor_selected_by(
                frame.parent, of_generation, f.has_ancestor.which
            ):
                return False
            result = True

        if result and "except_when" in f and f.except_when is not None:
            if any(self._is_selected_by(frame, c) for c in f.except_when):
                return False

        return result

    def evaluate_skip(self) -> Optional[SkippedActionReport]:
        """Decide whether to skip the action in the current_frame or not.

        Should be called in between self.begin_action and self.end_action, and before executing the action.

        Returns: Report regarding skipped action if it should be skipped, otherwise None.
        """

        if not self.config:
            return None

        if "include_action_when" in self.config and self.config.include_action_when:
            include = False
            for condition in self.config.include_action_when:
                if self._is_selected_by(self.current_frame, condition):
                    include = True
                    break
            if not include:
                return SkippedActionReport(
                    timestamp=StringBasedDateTime(arrow.utcnow()),
                    reason="None of the include_action_when conditions selected the action",
                    declaration=self.current_frame.action.declaration,
                )

        if "skip_action_when" in self.config and self.config.skip_action_when:
            for f, condition in enumerate(self.config.skip_action_when):
                if self._is_selected_by(self.current_frame, condition):
                    return SkippedActionReport(
                        timestamp=StringBasedDateTime(arrow.utcnow()),
                        reason=f"Action selected to be skipped by skip_action_when condition {f}",
                        declaration=self.current_frame.action.declaration,
                    )

        return None

    def begin_action(self, action: TestSuiteAction) -> None:
        if self.top_frame is None:
            self.top_frame = ActionStackFrame(action=action, parent=None, children=[])
            self.current_frame = self.top_frame
        else:
            self.current_frame = ActionStackFrame(
                action=action, parent=self.current_frame, children=[]
            )
            self.current_frame.parent.children.append(self.current_frame)

    def end_action(
        self, action: TestSuiteAction, report: TestSuiteActionReport
    ) -> None:
        if self.current_frame.action is not action:
            raise RuntimeError(
                f"Action {self.current_frame.action.declaration.get_action_type()} {self.current_frame.action.declaration.get_child_type()} was started, but a different action {action.declaration.get_action_type()} {action.declaration.get_child_type()} was ended"
            )
        self.current_frame.report = report
        self.current_frame = self.current_frame.parent
