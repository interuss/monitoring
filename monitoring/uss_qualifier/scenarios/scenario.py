import inspect
import traceback
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime
from enum import Enum
from typing import TypeVar

import arrow
from implicitdict import StringBasedDateTime
from loguru import logger

from monitoring import uss_qualifier as uss_qualifier_module
from monitoring.monitorlib import fetch, inspection
from monitoring.monitorlib.errors import current_stack_string
from monitoring.monitorlib.fetch import QueryType
from monitoring.monitorlib.inspection import fullname
from monitoring.uss_qualifier import scenarios as scenarios_module
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.reports.report import (
    ErrorReport,
    FailedCheck,
    Note,
    ParticipantID,
    PassedCheck,
    TestCaseReport,
    TestScenarioReport,
    TestStepReport,
)
from monitoring.uss_qualifier.resources.definitions import ResourceID
from monitoring.uss_qualifier.resources.resource import (
    MissingResourceError,
    ResourceType,
)
from monitoring.uss_qualifier.scenarios.definitions import (
    TestScenarioDeclaration,
    TestScenarioTypeName,
)
from monitoring.uss_qualifier.scenarios.documentation.definitions import (
    TestCaseDocumentation,
    TestCheckDocumentation,
    TestScenarioDocumentation,
    TestStepDocumentation,
)
from monitoring.uss_qualifier.scenarios.documentation.parsing import get_documentation

SQUELCH_WARN_ON_QUERY_TYPE = [
    # Posting an ISA is done for notifications: we can't always know the participant ID
    QueryType.F3411v19USSPostIdentificationServiceArea,
    QueryType.F3411v22aUSSPostIdentificationServiceArea,
    # When querying for display data and searching flights and their details, we don't always know the participant ID
    QueryType.InterUSSRIDObservationV1GetDisplayData,
    QueryType.InterUSSRIDObservationV1GetDetails,
    QueryType.F3411v19USSSearchFlights,
    QueryType.F3411v22aUSSSearchFlights,
    QueryType.F3411v19USSGetFlightDetails,
    QueryType.F3411v22aUSSGetFlightDetails,
]


class ScenarioCannotContinueError(Exception):
    def __init__(self, msg):
        super().__init__(msg)


class TestRunCannotContinueError(Exception):
    def __init__(self, msg):
        super().__init__(msg)


class ScenarioPhase(str, Enum):
    Undefined = "Undefined"
    NotStarted = "NotStarted"
    ReadyForTestCase = "ReadyForTestCase"
    ReadyForTestStep = "ReadyForTestStep"
    RunningTestStep = "RunningTestStep"
    ReadyForCleanup = "ReadyForCleanup"
    CleaningUp = "CleaningUp"
    Complete = "Complete"


class PendingCheck:
    _phase: ScenarioPhase
    _documentation: TestCheckDocumentation
    _step_report: TestStepReport
    _stop_fast: bool
    _on_failed_check: Callable[[FailedCheck], None] | None
    _participants: list[ParticipantID]
    _outcome_recorded: bool = False

    def __init__(
        self,
        phase: ScenarioPhase,
        documentation: TestCheckDocumentation,
        participants: list[ParticipantID],
        step_report: TestStepReport,
        stop_fast: bool,
        on_failed_check: Callable[[FailedCheck], None] | None,
    ):
        self._phase = phase
        self._documentation = documentation
        self._participants = participants
        self._step_report = step_report
        self._stop_fast = stop_fast
        self._on_failed_check = on_failed_check

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._outcome_recorded:
            self.record_passed()

    def record_failed(
        self,
        summary: str,
        details: str = "",
        query_timestamps: list[datetime] | None = None,
        additional_data: dict | None = None,
    ) -> None:
        self._outcome_recorded = True
        if "severity" in self._documentation and self._documentation.severity:
            severity = self._documentation.severity
        else:
            raise ValueError(
                f"Severity of check '{self._documentation.name}' was not specified at failure time and is not documented in scenario documentation"
            )

        if (
            self._stop_fast
            and severity != Severity.Critical
            and severity != Severity.Low
            and self._phase != ScenarioPhase.CleaningUp
        ):
            note = f"Severity {severity} upgraded to Critical because `stop_fast` flag set true in configuration"
            logger.info(note)
            details += "\n" + note
            severity = Severity.Critical

        kwargs = {
            "name": self._documentation.name,
            "documentation_url": self._documentation.url,
            "timestamp": StringBasedDateTime(arrow.utcnow()),
            "summary": summary,
            "details": details,
            "requirements": self._documentation.applicable_requirements,
            "severity": severity,
            "participants": self._participants,
        }
        if additional_data is not None:
            kwargs["additional_data"] = additional_data
        if query_timestamps is not None:
            kwargs["query_report_timestamps"] = [
                StringBasedDateTime(t) for t in query_timestamps
            ]
        failed_check = FailedCheck(**kwargs)
        self._step_report.failed_checks.append(failed_check)
        if self._on_failed_check is not None:
            self._on_failed_check(failed_check)
        if severity == Severity.High:
            raise ScenarioCannotContinueError(f"{severity}-severity issue: {summary}")
        if severity == Severity.Critical:
            raise TestRunCannotContinueError(f"{severity}-severity issue: {summary}")

    def record_passed(self) -> None:
        self._outcome_recorded = True

        passed_check = PassedCheck(
            name=self._documentation.name,
            timestamp=StringBasedDateTime(arrow.utcnow()),
            participants=self._participants,
            requirements=self._documentation.applicable_requirements,
        )
        self._step_report.passed_checks.append(passed_check)

    def skip(self) -> None:
        self._outcome_recorded = True

    def describe(self) -> str:
        doc = self._documentation
        severity = doc.severity or "NoSeverity"
        url = doc.url
        participant_str = (
            f" for participants {', '.join(self._participants)}"
            if getattr(self, "_participants", None)
            else ""
        )
        url_str = f", doc: {url}" if url else ""
        return f"'{doc.name} check' ({severity} severity involving {participant_str}) documented at {url_str})"


class ScenarioLogicError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)


class ScenarioDidNotStopError(ScenarioLogicError):
    def __init__(self, check: PendingCheck):
        super().__init__(
            f"Scenario did not stop as expected upon failed check: {check.describe()}"
        )


def get_scenario_type_by_name(scenario_type_name: TestScenarioTypeName) -> type:
    inspection.import_submodules(scenarios_module)
    scenario_type = inspection.get_module_object_by_name(
        parent_module=uss_qualifier_module, object_name=scenario_type_name
    )
    if not issubclass(scenario_type, TestScenario):
        raise NotImplementedError(
            f"Scenario type {scenario_type.__name__} is not a subclass of the TestScenario base class"
        )
    return scenario_type


class GenericTestScenario(ABC):
    """Generic Test Scenario allowing mutualization of test scenario implementation.

    Inherit from TestScenario class to define a test scenario ready to run.
    """

    declaration: TestScenarioDeclaration
    documentation: TestScenarioDocumentation
    on_failed_check: Callable[[FailedCheck], None] | None = None

    resource_origins: dict[ResourceID, str]
    """Map between local resource name (as defined in test scenario) to where that resource originated."""

    _phase: ScenarioPhase = ScenarioPhase.Undefined
    _scenario_report: TestScenarioReport | None = None
    _current_case: TestCaseDocumentation | None = None
    _case_report: TestCaseReport | None = None
    _current_step: TestStepDocumentation | None = None
    _step_report: TestStepReport | None = None

    _allow_undocumented_checks = False
    """When this variable is set to True, it allows undocumented checks to be executed by the scenario. This is primarly intended to simplify internal unit testing."""

    context = None
    """Execution context; set at begin_test_scenario."""

    def __init__(self):
        self.documentation = get_documentation(self.__class__)
        self._phase = ScenarioPhase.NotStarted

    @staticmethod
    def make_test_scenario(
        declaration: TestScenarioDeclaration,
        resource_pool: dict[ResourceID, ResourceType],
    ) -> "TestScenario":
        scenario_type = get_scenario_type_by_name(declaration.scenario_type)

        constructor_signature = inspect.signature(scenario_type.__init__)
        constructor_args = {}
        resource_origins = {}
        for arg_name, arg in constructor_signature.parameters.items():
            if arg_name == "self":
                continue
            if arg_name not in resource_pool:
                # Check if argument/resource is optional
                if arg.default != inspect.Parameter.empty:
                    # argument/resource is optional
                    continue

                # Missing value for required argument
                available_pool = ", ".join(resource_pool)
                raise MissingResourceError(
                    f'Resource to populate test scenario argument "{arg_name}" was not found in the resource pool when trying to create {declaration.scenario_type} test scenario (resource pool: {available_pool})',
                    arg_name,
                )
            constructor_args[arg_name] = resource_pool[arg_name]
            resource_origins[arg_name] = resource_pool[arg_name].resource_origin

        scenario = scenario_type(**constructor_args)
        scenario.declaration = declaration
        scenario.resource_origins = resource_origins
        return scenario

    @abstractmethod
    def run(self, context):
        """Execute the test scenario.

        Args:
            context: Execution context with type monitoring.uss_qualifier.suites.suite.ExecutionContext.  Type hint is
                not annotated because doing so would create a circular reference.
        """
        raise NotImplementedError(
            "A concrete test scenario must implement `run` method"
        )

    def cleanup(self):
        """Test scenarios needing to clean up after attempting to run should override this method."""
        self.skip_cleanup()

    def me(self) -> str:
        return inspection.fullname(self.__class__)

    def current_step_name(self) -> str | None:
        if self._current_step:
            return self._current_step.name
        else:
            return None

    def _make_scenario_report(self) -> None:
        self._scenario_report = TestScenarioReport(
            name=self.documentation.name,
            scenario_type=self.declaration.scenario_type,
            documentation_url=self.documentation.url,
            resource_origins=self.resource_origins,
            start_time=StringBasedDateTime(datetime.now(UTC)),
            cases=[],
        )

    def _expect_phase(self, expected_phase: ScenarioPhase | set[ScenarioPhase]):
        if isinstance(expected_phase, ScenarioPhase):
            expected_phase = {expected_phase}
        if self._phase not in expected_phase:
            caller = inspect.stack()[1].function
            acceptable_phases = ", ".join(expected_phase)
            raise RuntimeError(
                f"Test scenario `{self.me()}` was {self._phase} when {caller} was called (expected {acceptable_phases})"
            )

    def record_note(self, key: str, message: str) -> None:
        self._expect_phase(
            {
                ScenarioPhase.NotStarted,
                ScenarioPhase.ReadyForTestCase,
                ScenarioPhase.ReadyForTestStep,
                ScenarioPhase.RunningTestStep,
                ScenarioPhase.ReadyForCleanup,
                ScenarioPhase.CleaningUp,
            }
        )

        if self._scenario_report is None:
            self._make_scenario_report()

        if "notes" not in self._scenario_report:
            self._scenario_report.notes = {}

        if key in self._scenario_report.notes:
            # prevent notes from being overriden by adding a suffix if key is a duplicate
            suffix = 1
            while f"{key}_{suffix}" in self._scenario_report.notes:
                suffix += 1
            key += f"_{suffix}"

        self._scenario_report.notes[key] = Note(
            message=message,
            timestamp=StringBasedDateTime(arrow.utcnow().datetime),
        )
        logger.info(f"Note: {key} -> {message}")

    def begin_test_scenario(self, context) -> None:
        """Indicate that test scenario execution is beginning.

        Args:
            context: Execution context with type monitoring.uss_qualifier.suites.suite.ExecutionContext.  Type hint is
                not annotated because doing so would create a circular reference.
        """
        self.context = context
        self._expect_phase(ScenarioPhase.NotStarted)
        self._make_scenario_report()
        self._phase = ScenarioPhase.ReadyForTestCase

    def begin_test_case(self, name: str) -> None:
        self._expect_phase(ScenarioPhase.ReadyForTestCase)
        available_cases = {c.name: c for c in self.documentation.cases}
        if name not in available_cases:
            case_list = ", ".join(f'"{c}"' for c in available_cases)
            raise RuntimeError(
                f'Test scenario `{self.me()}` was instructed to begin_test_case "{name}", but that test case is not declared in documentation; declared cases are: {case_list}'
            )
        if name in [c.name for c in self._scenario_report.cases]:
            raise RuntimeError(
                f"Test case {name} had already run in `{self.me()}` when begin_test_case was called"
            )
        self._current_case = available_cases[name]
        self._case_report = TestCaseReport(
            name=self._current_case.name,
            documentation_url=self._current_case.url,
            start_time=StringBasedDateTime(datetime.now(UTC)),
            steps=[],
        )
        self._scenario_report.cases.append(self._case_report)
        self._phase = ScenarioPhase.ReadyForTestStep

    def begin_test_step(self, name: str) -> None:
        self._expect_phase(ScenarioPhase.ReadyForTestStep)
        available_steps = {c.name: c for c in self._current_case.steps}
        if name not in available_steps:
            step_list = ", ".join(f'"{s}"' for s in available_steps)
            raise RuntimeError(
                f'Test scenario `{self.me()}` was instructed to begin_test_step "{name}" during test case "{self._current_case.name}", but that test step is not declared in documentation; declared steps are: {step_list}'
            )
        self._begin_test_step(available_steps[name])

    def _begin_test_step(self, step: TestStepDocumentation) -> None:
        self._current_step = step
        self._step_report = TestStepReport(
            name=self._current_step.name,
            documentation_url=self._current_step.url,
            start_time=StringBasedDateTime(datetime.now(UTC)),
            failed_checks=[],
            passed_checks=[],
        )
        self._case_report.steps.append(self._step_report)
        self._phase = ScenarioPhase.RunningTestStep

    def record_queries(self, queries: list[fetch.Query]) -> None:
        for q in queries:
            self.record_query(q)

    def record_query(self, query: fetch.Query) -> None:
        self._expect_phase({ScenarioPhase.RunningTestStep, ScenarioPhase.CleaningUp})
        if "queries" not in self._step_report:
            self._step_report.queries = []
        for existing_query in self._step_report.queries:
            if query.request.timestamp == existing_query.request.timestamp:
                logger.error(
                    f"The same query ({query.query_type} to {query.participant_id} at {query.request.timestamp}) was recorded multiple times.  This is likely a bug in uss_qualifier at:\n{current_stack_string(2)}"
                )
                return
        self._step_report.queries.append(query)
        participant = (
            "UNKNOWN"
            if not query.has_field_with_value("participant_id")
            else query.participant_id
        )
        query_type = (
            "UNKNOWN"
            if not query.has_field_with_value("query_type")
            else query.query_type
        )
        # Log a warning if we are missing query metadata, unless the query type is one for which
        # we expect to occasionally not know the participant ID
        if (
            participant == "UNKNOWN" or query_type == "UNKNOWN"
        ) and query_type not in SQUELCH_WARN_ON_QUERY_TYPE:
            location = (
                traceback.format_list([traceback.extract_stack()[-2]])[0]
                .split("\n")[0]
                .strip()
            )
            logger.warning(
                f"Missing query metadata: {query.request['method']} {query.request['url']} has participant {participant} and type {query_type} at {location}"
            )

    def check(
        self,
        name: str,
        participants: ParticipantID | list[ParticipantID] | None = None,
    ) -> PendingCheck:
        if isinstance(participants, str):
            participants = [participants]
        self._expect_phase({ScenarioPhase.RunningTestStep, ScenarioPhase.CleaningUp})
        available_checks = {c.name: c for c in self._current_step.checks}
        if name in available_checks:
            check_documentation = available_checks[name]
        else:
            check_list = ", ".join(available_checks)
            if self._allow_undocumented_checks:
                # We create a dummy TestCheckDocumentation to continue.
                # The severity is unknown since we don't have documentation,
                # but we default to a medium severity (so a failure won't stop
                # tests).
                # These undocumented checks are primary used for unit testing,
                # this shouldn't have any impact on normal testing.
                check_documentation = TestCheckDocumentation(
                    name=name,
                    applicable_requirements=[],
                    has_todo=False,
                    severity=Severity.Medium,
                )
            else:
                test_step_name = (
                    self._current_step.name if self._current_step else "<none>"
                )
                test_case_name = (
                    self._current_case.name
                    if self._current_case
                    else "<none; possibly cleanup>"
                )
                raise RuntimeError(
                    f'Test scenario `{self.me()}` was instructed to prepare to record outcome for check "{name}" during test step "{test_step_name}" during test case "{test_case_name}", but that check is not declared in documentation; declared checks are: {check_list}'
                )
        return PendingCheck(
            phase=self._phase,
            documentation=check_documentation,
            participants=[] if participants is None else participants,
            step_report=self._step_report,
            stop_fast=self.context.stop_fast,
            on_failed_check=self.on_failed_check,
        )

    def end_test_step(self) -> TestStepReport:
        self._expect_phase(ScenarioPhase.RunningTestStep)
        self._step_report.end_time = StringBasedDateTime(datetime.now(UTC))
        self._current_step = None
        report = self._step_report
        self._step_report = None
        self._phase = ScenarioPhase.ReadyForTestStep
        return report

    def end_test_case(self) -> None:
        self._expect_phase(ScenarioPhase.ReadyForTestStep)
        self._case_report.end_time = StringBasedDateTime(datetime.now(UTC))
        self._current_case = None
        self._case_report = None
        self._phase = ScenarioPhase.ReadyForTestCase

    def end_test_scenario(self) -> None:
        self._expect_phase(ScenarioPhase.ReadyForTestCase)
        self._scenario_report.end_time = StringBasedDateTime(datetime.now(UTC))
        self._phase = ScenarioPhase.ReadyForCleanup

    def go_to_cleanup(self) -> None:
        self._expect_phase(
            {
                ScenarioPhase.ReadyForTestCase,
                ScenarioPhase.ReadyForTestStep,
                ScenarioPhase.RunningTestStep,
                ScenarioPhase.ReadyForCleanup,
            }
        )
        self._phase = ScenarioPhase.ReadyForCleanup

    def begin_cleanup(self) -> None:
        self._expect_phase(ScenarioPhase.ReadyForCleanup)
        if "cleanup" not in self.documentation or self.documentation.cleanup is None:
            raise RuntimeError(
                f"Test scenario `{self.me()}` attempted to begin_cleanup, but no cleanup step is documented"
            )
        self._current_step = self.documentation.cleanup
        self._step_report = TestStepReport(
            name=self._current_step.name,
            documentation_url=self._current_step.url,
            start_time=StringBasedDateTime(datetime.now(UTC)),
            failed_checks=[],
            passed_checks=[],
        )
        self._scenario_report.cleanup = self._step_report
        self._phase = ScenarioPhase.CleaningUp

    def skip_cleanup(self) -> None:
        self._expect_phase(ScenarioPhase.ReadyForCleanup)
        if "cleanup" in self.documentation and self.documentation.cleanup is not None:
            raise RuntimeError(
                f"Test scenario `{self.me()}` skipped cleanup even though a cleanup step is documented"
            )
        self._phase = ScenarioPhase.Complete

    def end_cleanup(self) -> None:
        self._expect_phase(ScenarioPhase.CleaningUp)
        self._step_report.end_time = StringBasedDateTime(datetime.now(UTC))
        self._phase = ScenarioPhase.Complete

    def ensure_cleanup_ended(self) -> None:
        """This method should be called if the scenario may or may not be done cleaning up.

        For instance, if an exception happened during cleanup and the exception may have been before or after
        end_cleanup was called."""
        self._expect_phase({ScenarioPhase.CleaningUp, ScenarioPhase.Complete})
        if self._phase == ScenarioPhase.CleaningUp:
            self._step_report.end_time = StringBasedDateTime(datetime.now(UTC))
            self._phase = ScenarioPhase.Complete

    def record_execution_error(self, e: Exception) -> None:
        if self._phase == ScenarioPhase.Complete:
            raise RuntimeError(
                f"Test scenario `{self.me()}` indicated an execution error even though it was already Complete"
            )
        if self._scenario_report is None:
            self._make_scenario_report()
        self._scenario_report.execution_error = ErrorReport.create_from_exception(e)
        self._scenario_report.successful = False
        self._phase = ScenarioPhase.Complete

    def get_report(self) -> TestScenarioReport:
        if self._scenario_report is None:
            self._make_scenario_report()
        if "execution_error" not in self._scenario_report:
            try:
                self._expect_phase(ScenarioPhase.Complete)
            except RuntimeError as e:
                self.record_execution_error(e)

        # Evaluate success
        self._scenario_report.successful = (
            "execution_error" not in self._scenario_report
        )
        for case_report in self._scenario_report.cases:
            for step_report in case_report.steps:
                for failed_check in step_report.failed_checks:
                    if failed_check.severity != Severity.Low:
                        self._scenario_report.successful = False
        if "cleanup" in self._scenario_report:
            for failed_check in self._scenario_report.cleanup.failed_checks:
                if failed_check.severity != Severity.Low:
                    self._scenario_report.successful = False

        return self._scenario_report


class TestScenario(GenericTestScenario):
    """Instance of a test scenario, ready to run after construction.

    Concrete subclasses of TestScenario must:
      1) Implement a constructor that accepts only parameters with types that are subclasses of Resource
      2) Call TestScenario.__init__ from the subclass's __init__
    """

    pass


def get_scenario_type_name(scenario_type: type[TestScenario]) -> TestScenarioTypeName:
    full_name = fullname(scenario_type)
    if not issubclass(scenario_type, TestScenario):
        raise ValueError(f"{full_name} is not a TestScenario")
    if not full_name.startswith("monitoring.uss_qualifier.scenarios"):
        raise ValueError(
            f"{full_name} does not appear to be located in the standard root path for test scenarios"
        )
    return TestScenarioTypeName(full_name[len("monitoring.uss_qualifier.") :])


TestScenarioType = TypeVar("TestScenarioType", bound=TestScenario)


def find_test_scenarios(
    module, already_checked: set[str] | None = None
) -> list[TestScenarioType]:
    if already_checked is None:
        already_checked = set()
    already_checked.add(module.__name__)
    test_scenarios = set()
    for name, member in inspect.getmembers(module):
        if (
            inspect.ismodule(member)
            and member.__name__ not in already_checked
            and member.__name__.startswith("monitoring.uss_qualifier.scenarios")
        ):
            descendants = find_test_scenarios(member, already_checked)
            for descendant in descendants:
                if descendant not in test_scenarios:
                    test_scenarios.add(descendant)
        elif inspect.isclass(member) and member is not TestScenario:
            if issubclass(member, TestScenario):
                if member not in test_scenarios:
                    test_scenarios.add(member)
    result = list(test_scenarios)
    result.sort(key=lambda s: fullname(s))
    return result
