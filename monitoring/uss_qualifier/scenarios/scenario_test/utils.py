import datetime
import importlib
from collections.abc import Callable

import arrow
from implicitdict import StringBasedDateTime
from loguru import logger

from monitoring.deployment_manager.infrastructure import Context
from monitoring.monitorlib.fetch import (
    Query,
    QueryType,
    RequestDescription,
    ResponseDescription,
)
from monitoring.monitorlib.testing import make_fake_url
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.reports.report import FailedCheck
from monitoring.uss_qualifier.requirements.definitions import RequirementID
from monitoring.uss_qualifier.scenarios.scenario import (
    GenericTestScenario,
    PendingCheck,
    ScenarioPhase,
    uss_qualifier_module,
)
from monitoring.uss_qualifier.scenarios.scenario import (
    TestCheckDocumentation as _TestCheckDocumentation,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario as _TestScenario
from monitoring.uss_qualifier.scenarios.scenario import (
    TestStepReport as _TestStepReport,
)


def build_fake_scenarios_module():
    """Build a fake module of scenarios, with the following classes
    Test
        - TestScenarioA
        - TestScenarioB
        - NotATestScenarioC
        SubModule:
            - TestScenarioSubA
            - TestScenarioSubB
            - TestScenarioB
            SubSubModule:
                - TestScenarioSubSubA

    TestScenarioA has a run method and can be instancied if needed
    """

    def _build_module(name: str):
        spec = importlib.machinery.ModuleSpec(
            f"monitoring.uss_qualifier.scenarios.{name}", None
        )
        return importlib.util.module_from_spec(spec)

    fake_module = _build_module("test")

    class TestScenarioA(_TestScenario):
        def __init__(self, test_resource, optional_test_resource=None):
            self.test_resource = test_resource
            self.optional_test_resource = optional_test_resource

        def run(self, context):
            pass

    class TestScenarioB(_TestScenario):
        pass

    class NotATestScenarioC:
        pass

    fake_module.TestScenarioA = TestScenarioA
    fake_module.TestScenarioB = TestScenarioB
    fake_module.NotATestScenarioC = NotATestScenarioC

    fake_sub_module = _build_module("test.submodule")

    class TestScenarioSubA(_TestScenario):
        pass

    class TestScenarioSubB(_TestScenario):
        pass

    fake_sub_module.TestScenarioSubA = TestScenarioSubA
    fake_sub_module.TestScenarioSubB = TestScenarioSubB
    fake_sub_module.TestScenarioB = TestScenarioB

    fake_subsub_module = _build_module("test.submodule.subsubmodule")

    class TestScenarioSubSubA(_TestScenario):
        pass

    fake_subsub_module.TestScenarioSubSubA = TestScenarioSubSubA

    fake_sub_module.subsubmodule = fake_subsub_module

    fake_module.submodule = fake_sub_module

    return fake_module


def assert_date_is_close_to_now(d: datetime.datetime):
    """Assert that a date is close to now (e.g. to ensure start_date has been recorded to now() during tests.
    We allow 10s of skew as a conservative value, eg. a *very* slow CPU"""
    assert abs((d - arrow.utcnow()).total_seconds()) < 10


def build_testable_pending_check(
    phase: ScenarioPhase | None = None,
    severity: Severity | None = None,
    stop_fast: bool = False,
    on_failed_check: Callable[[FailedCheck], None] | None = None,
) -> tuple[PendingCheck, _TestStepReport]:
    """Return a (PendingCheck, Report) instances with mocked relative objects"""

    if not phase:
        phase = ScenarioPhase.RunningTestStep

    documentation = _TestCheckDocumentation(
        name="test-doc-name",
        has_todo=False,
        url="test-doc-url",
        applicable_requirements=[RequirementID("test.req")],
    )

    if severity:
        documentation.severity = severity

    report = _TestStepReport(
        name="test-step-name",
        documentation_url="test-step-documentation-url",
        start_time=StringBasedDateTime(value=arrow.utcnow()),
        failed_checks=[],
        passed_checks=[],
    )

    pc = PendingCheck(
        phase=phase,
        documentation=documentation,
        participants=[ParticipantID("test-participant")],
        step_report=report,
        stop_fast=stop_fast,
        on_failed_check=on_failed_check,
    )

    return pc, report


class HideLogOutput:
    """Context manager that disable logging, usefull to hide messages/logs that are expected from the test and shouldn't be display to users"""

    def __enter__(self):
        logger.disable("monitoring.uss_qualifier.scenarios.scenario")

    def __exit__(self, *args):
        logger.enable("monitoring.uss_qualifier.scenarios.scenario")


def build_context(stop_fast: bool = False) -> Context:
    """Return a context that can be used with TestScenarios"""

    class DummyContext:
        stop_fast = False

    dc = DummyContext()
    dc.stop_fast = stop_fast

    return dc


def assert_runtime_is_state_error(e: Exception):
    """Assert that the passed exception has been raised dues to a wrong state in GenericTestScenario"""
    assert "was called (expected " in str(e)


def args_generator(call: str) -> list:
    """Return default arguments to pass to the function 'call' of a GenericTestScenario"""

    args = []

    if call == "begin_test_scenario":
        args = [build_context()]
    elif call == "begin_test_case":
        args = ["test-case-1"]
    elif call == "begin_test_step":
        args = ["test-step-1-1"]

    return args


def build_query() -> Query:
    """Return a query that can be used with record_query"""
    request = RequestDescription(
        method="HTTP-TEST",
        url=make_fake_url(),
        initiated_at=StringBasedDateTime(arrow.utcnow()),
    )
    response = ResponseDescription(
        elapsed_s=42, reported=StringBasedDateTime(arrow.utcnow())
    )

    return Query(
        request=request,
        response=response,
        participant_id=24,
        query_type=QueryType.F3411v19DSSSearchIdentificationServiceAreas,
    )


class InjectFakeScenariosModule:
    """Context manager that injects, in the uss_qualifier module a fake module generated by build_fake_scenarios_module"""

    def __enter__(self):
        fake_module = build_fake_scenarios_module()
        uss_qualifier_module.scenarios.test = fake_module
        return fake_module

    def __exit__(self, *args):
        del uss_qualifier_module.scenarios.test


def advance_new_gtsi_to_case(gtsi: GenericTestScenario):
    """Advance a fresh GenericTestScenario into a state where a case is running. Don't use this function if you expect a specific case"""
    gtsi.begin_test_scenario(build_context())
    gtsi.begin_test_case("test-case-1")


def advance_new_gtsi_to_step(gtsi: GenericTestScenario):
    """Advance a fresh GenericTestScenario into a state where a step is running. Don't use this function if you expect a specific step."""
    advance_new_gtsi_to_case(gtsi)
    gtsi.begin_test_step("test-step-1-1")


def advance_new_gtsi_before_cleanup(gtsi: GenericTestScenario):
    """Advance a fresh GenericTestScenario into a state just before cleanup should be done."""
    gtsi.begin_test_scenario(build_context())
    gtsi.go_to_cleanup()


def advance_new_gtsi_during_cleanup(gtsi: GenericTestScenario):
    """Advance a fresh GenericTestScenario into a state during cleanup is done."""
    advance_new_gtsi_before_cleanup(gtsi)
    gtsi.begin_cleanup()


def advance_new_gtsi_after_cleanup(gtsi: GenericTestScenario):
    """Advance a fresh GenericTestScenario into a state after cleanup is done done."""
    advance_new_gtsi_during_cleanup(gtsi)
    gtsi.end_cleanup()


def terminate_gtsi_during_step(gtsi: GenericTestScenario):
    """Terminate a GenericTestScenario currently running a step"""
    gtsi.end_test_step()
    terminate_gtsi_during_case(gtsi)


def terminate_gtsi_during_case(gtsi: GenericTestScenario):
    """Terminate a GenericTestScenario currently running a step"""
    gtsi.end_test_case()
    terminate_gtsi_during_scenario(gtsi)


def terminate_gtsi_during_scenario(gtsi: GenericTestScenario):
    """Terminate a GenericTestScenario currently running a step"""
    gtsi.end_test_scenario()
    gtsi.begin_cleanup()
    gtsi.end_cleanup()


def run_a_set_of_calls_on_gtsi(gtsi: GenericTestScenario, calls: list[str]):
    """Run a list of call on the GenericTestScenario, with default arguments"""

    for call in calls:
        if call == "nop":
            continue

        getattr(gtsi, call)(*args_generator(call))


class ErrorForTests(Exception):
    pass
