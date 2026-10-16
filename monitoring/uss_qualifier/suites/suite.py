from __future__ import annotations

import json
import os
import re
from collections.abc import Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from copy import copy
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Condition

import arrow
import yaml
from implicitdict import StringBasedDateTime
from loguru import logger

from monitoring.monitorlib.dicts import JSONAddress
from monitoring.monitorlib.fetch import Query
from monitoring.monitorlib.fileio import resolve_filename
from monitoring.monitorlib.inspection import fullname
from monitoring.monitorlib.temporal import Time, TimeDuringTest
from monitoring.monitorlib.versioning import repo_url_of
from monitoring.uss_qualifier import package_root
from monitoring.uss_qualifier.action_generators.action_generator import (
    ActionGenerator,
    action_generator_type_from_name,
)
from monitoring.uss_qualifier.action_generators.documentation.documentation import (
    list_potential_actions_for_action_generator_definition,
)
from monitoring.uss_qualifier.configurations.configuration import (
    ExecutionConfiguration,
    FullyQualifiedCheck,
    TestSuiteActionSelectionCondition,
)
from monitoring.uss_qualifier.reports.capabilities import (
    evaluate_condition_for_test_suite,
)
from monitoring.uss_qualifier.reports.report import (
    ActionGeneratorReport,
    FailedCheck,
    ParticipantCapabilityEvaluationReport,
    Severity,
    SkippedActionReport,
    TestScenarioReport,
    TestSuiteActionReport,
    TestSuiteReport,
)
from monitoring.uss_qualifier.resources.definitions import ResourceID
from monitoring.uss_qualifier.resources.resource import (
    MissingResourceError,
    ResourceType,
    create_resources,
    make_child_resources,
)
from monitoring.uss_qualifier.scenarios.scenario import (
    ScenarioCannotContinueError,
    TestRunCannotContinueError,
    TestScenario,
    are_scenario_types_equal,
    fully_qualified_check_in_collection,
    get_scenario_type_by_name,
)
from monitoring.uss_qualifier.suites.definitions import (
    TestSuiteActionDeclaration,
    TestSuiteDeclaration,
    TestSuiteDefinition,
)

TEST_RUN_TIMEOUT_SKIP_REASON = "Maximum test run time has been exceeded"


def _print_failed_check(failed_check: FailedCheck) -> None:
    yaml_lines = yaml.dump(json.loads(json.dumps(failed_check))).split("\n")
    if failed_check.severity == Severity.Low:
        logger.info(
            "Informational finding:\n{}", "\n".join("  " + line for line in yaml_lines)
        )
    else:
        logger.warning(
            "New failed check:\n{}", "\n".join("  " + line for line in yaml_lines)
        )


class TestSuiteAction[T: ActionGenerator]:
    declaration: TestSuiteActionDeclaration
    test_scenario: TestScenario | None = None
    test_suite: TestSuite | None = None
    action_generator: T | None = None

    def __init__(
        self,
        action: TestSuiteActionDeclaration,
        resources: dict[ResourceID, ResourceType],
    ):
        self.declaration = action
        resources_for_child = make_child_resources(
            resources,
            action.get_resource_links(),
            f"Test suite action to run {action.get_action_type_name()} {action.get_child_type()}",
        )

        if "test_scenario" in action and action.test_scenario:
            self.test_scenario = TestScenario.make_test_scenario(
                declaration=action.test_scenario, resource_pool=resources_for_child
            )
        elif "test_suite" in action and action.test_suite:
            self.test_suite = TestSuite(
                declaration=action.test_suite,
                resources=resources,
            )
        elif "action_generator" in action and action.action_generator:
            self.action_generator = ActionGenerator.make_from_definition(
                definition=action.action_generator, resources=resources_for_child
            )
        else:
            raise action.invalid_type_error

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
        """Run an action whose frame has already been registered in the context."""
        skip_report = context.evaluate_skip()
        if skip_report:
            logger.warning(
                f"Skipping {self.declaration.get_action_type_name()} '{self.get_name()}' because: {skip_report.reason}"
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

        if not scenario:
            raise Exception("Cannot execute _run_test_scenario when no scenario is set")

        logger.info(f'Running "{scenario.documentation.name}" scenario...')
        scenario.on_failed_check = _print_failed_check
        scenario.time_context[TimeDuringTest.StartOfTestRun] = Time(context.start_time)
        scenario.time_context[TimeDuringTest.StartOfScenario] = Time(
            arrow.utcnow().datetime
        )

        try:
            # Full asyncio: await run/cleanup and aclose on the executing task's
            # loop rather than entering this synchronous Runner bridge.
            with scenario.async_runtime():
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
            scenario.record_execution_error(e, allow_after_completion=True)
        report = scenario.get_report()
        if "execution_error" in report and report.execution_error:
            lines = report.execution_error.stacktrace.split("\n")
            logger.error(
                'Execution error in scenario "{}":\n{}',
                scenario.documentation.name,
                "\n".join("  " + line for line in lines),
            )
        else:
            logger.info(f'"{scenario.documentation.name}" scenario completed')
        return report

    def _run_test_suite(self, context: ExecutionContext) -> TestSuiteReport:
        if not self.test_suite:
            raise Exception("Cannot execute _run_test_suite when no test suite is set")

        logger.info(f"Beginning test suite {self.test_suite.definition.name}...")
        report = self.test_suite.run(context)
        logger.info(f"Completed test suite {self.test_suite.definition.name}")
        return report

    def _run_action_generator(self, context: ExecutionContext) -> ActionGeneratorReport:
        if not self.action_generator:
            raise Exception(
                "Cannot execute _run_action_generator when no action generator is set"
            )

        report = ActionGeneratorReport(
            actions=[],
            generator_type=self.action_generator.definition.generator_type,
            start_time=StringBasedDateTime(arrow.utcnow()),
        )

        _run_actions(self.action_generator.actions(), context, report)

        return report


class TestSuite:
    declaration: TestSuiteDeclaration
    definition: TestSuiteDefinition
    documentation_url: str
    actions: list[TestSuiteAction | SkippedActionReport]

    def __init__(
        self,
        declaration: TestSuiteDeclaration,
        resources: dict[ResourceID, ResourceType],
    ):
        # Determine the suite's documentation URL
        if "suite_type" in declaration and declaration.suite_type:
            suite_yaml_path = resolve_filename(declaration.suite_type, package_root)
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
            local_resources = create_resources(
                self.definition.local_resources,
                self.declaration.type_name,
                base_resource_pool=self.local_resources,
            )
            for local_resource_id, resource in local_resources.items():
                if local_resource_id not in self.local_resources:
                    self.local_resources[local_resource_id] = resource
                elif local_resource_id in self.definition.local_resources:
                    logger.debug(
                        f"Overriding local resource {local_resource_id} in test suite {declaration.suite_type} with externally-provided resource"
                    )

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
            ].is_or_inherits(resource_type):
                raise ValueError(
                    f'Test suite "{self.definition.name}" expected resource {resource_id} to be {resource_type}, but instead it was provided {fullname(self.local_resources[resource_id].__class__)}'
                )
        actions: list[TestSuiteAction | SkippedActionReport] = []
        for a, action_dec in enumerate(self.definition.actions):
            try:
                actions.append(
                    TestSuiteAction(action=action_dec, resources=self.local_resources)
                )
            except MissingResourceError as e:
                logger.warning(
                    f"Skipping action {a} ({action_dec.get_action_type_name()} {action_dec.get_child_type()}) because {str(e)}"
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
            start_time=StringBasedDateTime(datetime.now(UTC)),
            actions=[],
            capability_evaluations=[],
        )

        def actions() -> Iterator[TestSuiteAction | SkippedActionReport]:
            yield from self.actions

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
    actions: Iterator[TestSuiteAction | SkippedActionReport],
    context: ExecutionContext,
    report: TestSuiteReport | ActionGeneratorReport,
) -> None:
    max_parallelism = context.max_parallelism()

    # Each invocation has its own capacity, including nested suites and generators.
    condition = Condition()  # Coordination signal for action-continuation checks
    active = 0  # Number of active actions
    stop_dispatch = False  # Flag to stop dispatching actions
    results: list[Future[TestSuiteActionReport] | TestSuiteActionReport] = []

    def run_action(
        action: TestSuiteAction, action_context: ExecutionContext
    ) -> TestSuiteActionReport:
        nonlocal active, stop_dispatch
        try:
            action_report = action.run(action_context)
            with condition:
                stop_dispatch |= action_report.has_critical_problem()
            return action_report
        except BaseException:
            with condition:
                stop_dispatch = True
            raise
        finally:
            with condition:
                active -= 1
                condition.notify()

    with ThreadPoolExecutor(max_workers=max_parallelism) as executor:
        while True:
            # Wait until we're below max parallelism to dispatch the next action
            with condition:
                condition.wait_for(lambda: active < max_parallelism or stop_dispatch)
                if stop_dispatch:
                    break

            # Advance to next action using actions as a lazy generator
            try:
                action = next(actions)
            except StopIteration:
                break

            with condition:
                # An action may have completed while the generator was advancing.
                if stop_dispatch:
                    break
                if isinstance(action, SkippedActionReport):
                    results.append(TestSuiteActionReport(skipped_action=action))
                else:
                    # Register frames before submitting so addresses follow dispatch order.
                    action_context = context.fork(
                        action, len(report.actions) + len(results)
                    )
                    if context.should_stop_early_now():
                        action_report = TestSuiteActionReport(
                            skipped_action=SkippedActionReport(
                                timestamp=StringBasedDateTime(arrow.utcnow().datetime),
                                reason=TEST_RUN_TIMEOUT_SKIP_REASON,
                                declaration=action.declaration,
                            )
                        )
                        action_context.end_action(action, action_report)
                        results.append(action_report)
                    else:
                        active += 1
                        results.append(
                            executor.submit(run_action, action, action_context)
                        )

        # Already-dispatched actions finish even when subsequent dispatch is stopped.
        report.actions.extend(
            result.result() if isinstance(result, Future) else result
            for result in results
        )
    report.successful = all(
        not a.has_critical_problem() and a.successful() for a in report.actions
    )
    report.end_time = StringBasedDateTime(datetime.now(UTC))


@dataclass
class ActionStackFrame:
    action: TestSuiteAction
    parent: ActionStackFrame | None
    children: list[ActionStackFrame]
    report: TestSuiteActionReport | None = None
    index: int = 0

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

        return f"{self.parent.address()}.actions[{self.index}].{addr}"


class ExecutionContext:
    start_time: datetime
    config: ExecutionConfiguration | None
    acceptable_findings: list[FullyQualifiedCheck]
    top_frame: ActionStackFrame | None
    current_frame: ActionStackFrame | None

    def __init__(
        self,
        config: ExecutionConfiguration | None,
        acceptable_findings: list[FullyQualifiedCheck],
    ):
        self.config = config
        self.acceptable_findings = acceptable_findings
        self.top_frame = None
        self.current_frame = None
        self.start_time = arrow.utcnow().datetime

    def fork(self, action: TestSuiteAction, index: int) -> ExecutionContext:
        """Share the report tree and run configuration, but keep a private frame cursor."""
        context = copy(self)
        context.begin_action(action, index)
        return context

    def sibling_queries(self) -> Iterator[Query]:
        if self.current_frame is None or self.current_frame.parent is None:
            return
        for child in self.current_frame.parent.children:
            if child.report is not None:
                yield from child.report.queries()

    def find_test_scenario_reports(
        self, scenario_type: type[TestScenario]
    ) -> list[TestScenarioReport]:
        """Find reports for all currently-completed instances of the specified test scenario type."""
        return [
            report
            for report in self.test_scenario_reports()
            if issubclass(
                get_scenario_type_by_name(report.scenario_type), scenario_type
            )
        ]

    def test_scenario_reports(
        self, frame: ActionStackFrame | None = None
    ) -> Iterator[TestScenarioReport]:
        if not frame:
            frame = self.top_frame
            if not frame:
                return
        if (
            frame.report is not None
            and "test_scenario" in frame.report
            and frame.report.test_scenario is not None
        ):
            yield frame.report.test_scenario
        for child in frame.children:
            yield from self.test_scenario_reports(child)

    def stop_fast(
        self, test_case_name: str, test_step_name: str, check_name: str
    ) -> bool:
        if (
            self.config is not None
            and "stop_fast" in self.config
            and self.config.stop_fast
        ):
            if (
                "do_not_stop_fast_for_acceptable_findings" in self.config
                and self.config.do_not_stop_fast_for_acceptable_findings
            ):
                # See if there is an exception for the particular check being considered
                if self.current_frame and self.current_frame.action.test_scenario:
                    current_check = FullyQualifiedCheck(
                        scenario_type=self.current_frame.action.test_scenario.declaration.scenario_type,
                        test_case_name=test_case_name,
                        test_step_name=test_step_name,
                        check_name=check_name,
                    )
                    if fully_qualified_check_in_collection(
                        current_check, self.acceptable_findings
                    ):
                        return False
            return True
        return False

    def should_stop_early_now(self) -> bool:
        if (
            not self.config
            or "stop_after" not in self.config
            or not self.config.stop_after
        ):
            return False
        dt = arrow.utcnow() - self.start_time
        return dt >= self.config.stop_after.timedelta

    def max_parallelism(self) -> int:
        if not self.config or not self.config.parallelism_rules:
            return 1
        if not self.current_frame:
            return 1
        for rule in self.config.parallelism_rules:
            if any(
                self._is_selected_by(self.current_frame, condition)
                for condition in rule.conditions
            ):
                return rule.max_parallelism
        return 1

    def _compute_n_of(
        self, target: TestSuiteAction, condition: TestSuiteActionSelectionCondition
    ) -> int:
        n = 0
        queue: list[ActionStackFrame] = []

        if self.top_frame:
            queue.append(self.top_frame)

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
        frame: ActionStackFrame | None,
        of_generation: int | None,
        which: list[TestSuiteActionSelectionCondition],
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
                if (
                    f.is_action_generator.potentially_generates_all_of is not None
                    or f.is_action_generator.potentially_generates_any_of is not None
                ):
                    potential_actions = (
                        list_potential_actions_for_action_generator_definition(
                            action.action_generator.definition
                        )
                    )
                    if (
                        f.is_action_generator.potentially_generates_all_of is not None
                        and not all(
                            a in potential_actions
                            for a in f.is_action_generator.potentially_generates_all_of
                        )
                    ):
                        return False
                    if (
                        f.is_action_generator.potentially_generates_any_of is not None
                        and not any(
                            a in potential_actions
                            for a in f.is_action_generator.potentially_generates_any_of
                        )
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
                    matches_scenario_type = False
                    for scenario_type in f.is_test_scenario.types:
                        if are_scenario_types_equal(
                            scenario_type,
                            action.test_scenario.declaration.scenario_type,
                        ):
                            matches_scenario_type = True
                            break
                    if not matches_scenario_type:
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

    def evaluate_skip(self) -> SkippedActionReport | None:
        """Decide whether to skip the action in the current_frame or not.

        Should be called in between self.begin_action and self.end_action, and before executing the action.

        Returns: Report regarding skipped action if it should be skipped, otherwise None.
        """

        if not self.config:
            return None

        if not self.current_frame:
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

        if (
            "scenarios_filter" in self.config
            and self.config.scenarios_filter
            and self.current_frame.action.test_scenario
        ):
            scenario_type = (
                self.current_frame.action.test_scenario.declaration.scenario_type
            )
            if not re.search(self.config.scenarios_filter, scenario_type):
                return SkippedActionReport(
                    timestamp=StringBasedDateTime(arrow.utcnow()),
                    reason=f"Scenario type '{scenario_type}' did not match against scenarios_filter regex `{self.config.scenarios_filter}`",
                    declaration=self.current_frame.action.declaration,
                )

        return None

    def begin_action(self, action: TestSuiteAction, index: int | None = None) -> None:
        if self.top_frame is None:
            self.top_frame = ActionStackFrame(action=action, parent=None, children=[])
            self.current_frame = self.top_frame
        else:
            if index is None:
                index = len(self.current_frame.children) if self.current_frame else 0
            self.current_frame = ActionStackFrame(
                action=action,
                parent=self.current_frame,
                children=[],
                index=index,
            )
            if self.current_frame.parent:
                self.current_frame.parent.children.append(self.current_frame)

    def end_action(
        self, action: TestSuiteAction, report: TestSuiteActionReport
    ) -> None:
        if not self.current_frame:
            raise RuntimeError(
                "end_action has been called, but there is not current frame"
            )

        if self.current_frame.action is not action:
            raise RuntimeError(
                f"Action {self.current_frame.action.declaration.get_action_type_name()} {self.current_frame.action.declaration.get_child_type()} was started, but a different action {action.declaration.get_action_type_name()} {action.declaration.get_child_type()} was ended"
            )
        self.current_frame.report = report
        self.current_frame = self.current_frame.parent
