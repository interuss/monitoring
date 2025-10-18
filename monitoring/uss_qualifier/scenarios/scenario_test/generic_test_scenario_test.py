import itertools

from monitoring.uss_qualifier.resources.dev.noop import NoOpResource, NoOpSpecification
from monitoring.uss_qualifier.resources.resource import MissingResourceError
from monitoring.uss_qualifier.scenarios.scenario import (
    GenericTestScenario,
    ScenarioCannotContinueError,
)
from monitoring.uss_qualifier.scenarios.scenario import (
    TestRunCannotContinueError as _TestRunCannotContinueError,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario as _TestScenario
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenarioDeclaration as _TestScenarioDeclaration,
)

from .generic_test_scenario_without_cleanup import (
    build_generic_test_scenario_instance_without_cleanup,
)
from .utils import (
    ErrorForTests,
    HideLogOutput,
    InjectFakeScenariosModule,
    advance_new_gtsi_before_cleanup,
    advance_new_gtsi_during_cleanup,
    advance_new_gtsi_to_case,
    advance_new_gtsi_to_step,
    args_generator,
    assert_date_is_close_to_now,
    assert_runtime_is_state_error,
    build_context,
    build_query,
    run_a_set_of_calls_on_gtsi,
    terminate_gtsi_during_case,
    terminate_gtsi_during_scenario,
    terminate_gtsi_during_step,
)


def _build_generic_test_scenario_instance() -> _TestScenario:
    """Return a GenericTestScenario instance that can be used to test various methods. This function is not in utils to keep the markdown definition local to this file"""

    declaration = _TestScenarioDeclaration(
        scenario_type="scenarios.test.GenericTestScenarioForTests"
    )

    class GenericTestScenarioForTests(_TestScenario):
        def run(self, context):
            pass

    gtsi = GenericTestScenarioForTests()
    gtsi.declaration = declaration
    gtsi.resource_origins = {"test-resource": "test-origin"}

    return gtsi


def test_make_test_scenario_base():
    """Test the scenario returned by make_test_scenario in the normal case"""

    with InjectFakeScenariosModule():
        declaration = _TestScenarioDeclaration(
            scenario_type="scenarios.test.TestScenarioA"
        )

        scenario = GenericTestScenario.make_test_scenario(
            declaration,
            {
                "test_resource": NoOpResource(
                    NoOpSpecification(sleep_secs=42), "test-origin"
                )
            },
        )

        assert scenario.__class__.__name__ == "TestScenarioA"
        assert scenario.declaration == declaration
        assert "test_resource" in scenario.resource_origins
        assert scenario.resource_origins["test_resource"] == "test-origin"
        assert scenario.test_resource.sleep_secs == 42
        assert "optional_test_resource" not in scenario.resource_origins


def test_make_test_scenario_missing_resource():
    """Test that make_test_scenario is raising exceptions when resources are missing"""

    with InjectFakeScenariosModule():
        declaration = _TestScenarioDeclaration(
            scenario_type="scenarios.test.TestScenarioA"
        )

        try:
            GenericTestScenario.make_test_scenario(declaration, {})
            assert False  # MissingResourceError should have been raised
        except MissingResourceError:
            pass


def test_make_test_scenario_resource():
    """Test the make_test_scenario method process resources correctly"""

    with InjectFakeScenariosModule():
        declaration = _TestScenarioDeclaration(
            scenario_type="scenarios.test.TestScenarioA"
        )

        scenario = GenericTestScenario.make_test_scenario(
            declaration,
            {
                "test_resource": NoOpResource(
                    NoOpSpecification(sleep_secs=42), "test-origin"
                ),
                "optional_test_resource": NoOpResource(
                    NoOpSpecification(sleep_secs=24), "test-origin-2"
                ),
            },
        )
        assert "test_resource" in scenario.resource_origins
        assert scenario.resource_origins["test_resource"] == "test-origin"
        assert scenario.test_resource.sleep_secs == 42
        assert "optional_test_resource" in scenario.resource_origins
        assert scenario.resource_origins["optional_test_resource"] == "test-origin-2"
        assert scenario.optional_test_resource.sleep_secs == 24


def test_me():
    """Ensure the me() function is returning the name of the test scenario"""

    gtsi = _build_generic_test_scenario_instance()

    assert (
        gtsi.me()
        == "monitoring.uss_qualifier.scenarios.scenario_test.generic_test_scenario_test._build_generic_test_scenario_instance.<locals>.GenericTestScenarioForTests"
    )


def test_cleanup():
    """Test the default cleanup function of GenericTestScenario, that should call `skip_cleanup` when not overridden by others classes"""

    gtsi = _build_generic_test_scenario_instance()

    skip_cleanup_called = False

    def skip_cleanup():
        nonlocal skip_cleanup_called
        skip_cleanup_called = True

    gtsi.skip_cleanup = skip_cleanup

    gtsi.cleanup()

    assert skip_cleanup_called


def test_current_step_name():
    """That the current_step_name function by evaluating results at various steps of a TestScenario life"""

    gtsi = _build_generic_test_scenario_instance()

    assert gtsi.current_step_name() is None

    gtsi.begin_test_scenario(build_context())
    assert gtsi.current_step_name() is None

    gtsi.begin_test_case("test-case-1")
    assert gtsi.current_step_name() is None

    gtsi.begin_test_step("test-step-1-1")
    assert gtsi.current_step_name() == "test-step-1-1"

    gtsi.end_test_step()
    assert gtsi.current_step_name() is None

    gtsi.begin_test_step("test-step-1-2")
    assert gtsi.current_step_name() == "test-step-1-2"

    gtsi.end_test_step()
    assert gtsi.current_step_name() is None

    gtsi.end_test_case()
    assert gtsi.current_step_name() is None

    gtsi.end_test_scenario()
    assert gtsi.current_step_name() is None


def test_state_machine():
    """Test the flow of a GenericTestScenario, by testing impossible call orders an ensuring errors are generated"""

    # We limit ourself to a basic flow without cleanup, to avoid too many test
    # to do. Others tests also test the state of the test for function,
    # ensuring full coverage
    possible_calls = [
        "begin_test_scenario",
        "begin_test_case",
        "begin_test_step",
        "end_test_step",
        "end_test_case",
        "end_test_scenario",
    ]

    for call_order in itertools.permutations(possible_calls, len(possible_calls)):
        gtsi = _build_generic_test_scenario_instance()
        failled = False

        for call in call_order:
            try:
                getattr(gtsi, call)(*args_generator(call))
            except RuntimeError as e:
                assert_runtime_is_state_error(e)
                failled = True
                break

        # Only one ordering is possible, everything else should fail
        assert failled != (
            ",".join(call_order)
            == "begin_test_scenario,begin_test_case,begin_test_step,end_test_step,end_test_case,end_test_scenario"
        )


def test_begin_test_scenario_base():
    """Tet the begin_test_scenario function in the basic case"""

    gtsi = _build_generic_test_scenario_instance()
    gtsi.begin_test_scenario({"test-context": "test-context-value"})

    # Check that begin_test_scenario is recording context
    assert gtsi.context == {"test-context": "test-context-value"}


def test_begin_test_scenario_twice():
    """Test the begin_test_scenario function cannot be called twice"""

    gtsi = _build_generic_test_scenario_instance()
    gtsi.begin_test_scenario(build_context())

    try:
        gtsi.begin_test_scenario(build_context())
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)


def test_begin_test_case():
    """Tet the begin_test_case function in the basic case"""

    gtsi = _build_generic_test_scenario_instance()

    # Test that we must run begin_test_scenario first
    try:
        gtsi.begin_test_case("test-case-1")
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_scenario(build_context())
    gtsi.begin_test_case("test-case-1")


def test_begin_test_case_twice():
    """Test the begin_test_case function cannot be called twice"""

    gtsi = _build_generic_test_scenario_instance()
    gtsi.begin_test_scenario(build_context())
    gtsi.begin_test_case("test-case-1")

    # Test that we cannot run begin_test_case twice
    try:
        gtsi.begin_test_case("test-case-1")
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)


def test_begin_test_case_after_ending_test_case():
    """Test the begin_test_case function can be called again after ending a test case"""

    gtsi = _build_generic_test_scenario_instance()
    gtsi.begin_test_scenario(build_context())
    gtsi.begin_test_case("test-case-1")
    gtsi.end_test_case()
    gtsi.begin_test_case("test-case-2")
    gtsi.end_test_case()


def test_begin_test_case_duplicate():
    """Test the begin_test_case function cannot start a test case twice"""

    gtsi = _build_generic_test_scenario_instance()
    gtsi.begin_test_scenario(build_context())
    gtsi.begin_test_case("test-case-1")
    gtsi.end_test_case()

    try:
        gtsi.begin_test_case("test-case-1")
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert "Test case test-case-1 had already run in" in str(e)


def test_begin_test_case_unknown():
    """Test the begin_test_case function cannot start a unknown test case"""

    gtsi = _build_generic_test_scenario_instance()
    gtsi.begin_test_scenario(build_context())

    try:
        gtsi.begin_test_case("not-a-test-case-1")
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert (
            'was instructed to begin_test_case "not-a-test-case-1", but that test case is not declared in documentation'
            in str(e)
        )


def test_begin_test_step():
    """Tet the begin_test_step function in the basic case"""

    gtsi = _build_generic_test_scenario_instance()

    # Test that we must run begin_test_scenario and begin_test_case first
    try:
        gtsi.begin_test_step("test-step-1-1")
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_scenario(build_context())

    try:
        gtsi.begin_test_step("test-step-1-1")
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_case("test-case-1")

    gtsi.begin_test_step("test-step-1-1")


def test_begin_test_step_twice():
    """Test the begin_test_step function cannot be called twice"""

    gtsi = _build_generic_test_scenario_instance()
    gtsi.begin_test_scenario(build_context())
    gtsi.begin_test_case("test-case-1")
    gtsi.begin_test_step("test-step-1-1")

    try:
        gtsi.begin_test_step("test-step-1-1")
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)


def test_begin_test_step_after_ending_step():
    """Test the begin_test_step function can be called again after ending step"""

    gtsi = _build_generic_test_scenario_instance()
    gtsi.begin_test_scenario(build_context())
    gtsi.begin_test_case("test-case-1")
    gtsi.begin_test_step("test-step-1-1")
    gtsi.end_test_step()
    gtsi.begin_test_step("test-step-1-2")


def test_begin_test_step_unkown():
    """Test the begin_test_step function can be called on unknown test steps"""

    gtsi = _build_generic_test_scenario_instance()
    gtsi.begin_test_scenario(build_context())
    gtsi.begin_test_case("test-case-1")

    try:
        gtsi.begin_test_step("not-a-test-step")
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert (
            'was instructed to begin_test_step "not-a-test-step" during test case "test-case-1", but that test step is not declared in documentation'
            in str(e)
        )


def test_end_test_step():
    """Test end_test_step in the basic case"""

    gtsi = _build_generic_test_scenario_instance()

    # Test that we must run have called begin_test_step first
    try:
        gtsi.end_test_step()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_scenario(build_context())

    try:
        gtsi.end_test_step()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_case("test-case-1")

    try:
        gtsi.end_test_step()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_step("test-step-1-1")
    gtsi.end_test_step()


def test_end_test_step_twice():
    """Test that we cannot call end_test_step twice"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_to_step(gtsi)
    gtsi.end_test_step()

    try:
        gtsi.end_test_step()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)


def test_end_test_step_report():
    """Ensure end_test_step is returning a report about the test step"""

    gtsi = _build_generic_test_scenario_instance()
    gtsi.begin_test_scenario(build_context())
    gtsi.begin_test_case("test-case-1")

    gtsi.begin_test_step("test-step-1-2")
    report = gtsi.end_test_step()

    assert report
    assert report.name == "test-step-1-2"
    # Start and end date of the report should be close to now
    assert_date_is_close_to_now(report.start_time.datetime)
    assert report.end_time
    assert_date_is_close_to_now(report.end_time.datetime)


def test_end_test_case():
    """Test the end_test_case in the basic case"""

    gtsi = _build_generic_test_scenario_instance()

    # Test that we must run have called begin_test_case first
    try:
        gtsi.end_test_case()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_scenario(build_context())

    try:
        gtsi.end_test_case()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_case("test-case-1")
    gtsi.end_test_case()


def test_end_test_case_twice():
    """Test that end_test_case cannot be called twice"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_to_case(gtsi)
    gtsi.end_test_case()

    try:
        gtsi.end_test_case()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)


def test_end_test_scenario():
    """Test the end_test_scenario in the basic case"""

    gtsi = _build_generic_test_scenario_instance()

    # Test that we must run have called begin_test_scenario first
    try:
        gtsi.end_test_scenario()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_scenario(build_context())
    gtsi.end_test_scenario()


def test_end_test_scenario_twice():
    """Test that we cannot call end_test_scenario twice"""

    gtsi = _build_generic_test_scenario_instance()
    gtsi.begin_test_scenario(build_context())
    gtsi.end_test_scenario()

    try:
        gtsi.end_test_scenario()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)


def test_go_to_cleanup():
    """Test the go_to_cleanup is callabled when it's expected to be callable"""

    # This is a list of step to do, in order, and if go_to_cleanup should works
    steps_and_result = [
        ("nop", False),
        ("begin_test_scenario", True),
        ("begin_test_case", True),
        ("begin_test_step", True),
        ("end_test_step", True),
        ("end_test_case", True),
        ("end_test_scenario", True),
        ("go_to_cleanup", True),
        ("begin_cleanup", False),
        ("end_cleanup", False),
    ]

    for steps_to_do in range(1, len(steps_and_result) + 1):
        steps_and_result_to_test = steps_and_result[:steps_to_do]

        gtsi = _build_generic_test_scenario_instance()

        run_a_set_of_calls_on_gtsi(gtsi, [step for step, _ in steps_and_result_to_test])

        success = True
        try:
            gtsi.go_to_cleanup()
        except RuntimeError as e:
            assert_runtime_is_state_error(e)
            success = False

        assert success == steps_and_result_to_test[-1][1]


def test_begin_cleanup():
    """Test the begin_cleanup base case"""

    gtsi = _build_generic_test_scenario_instance()

    try:
        gtsi.begin_cleanup()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_scenario(build_context())

    try:
        gtsi.begin_cleanup()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.go_to_cleanup()
    gtsi.begin_cleanup()


def test_begin_cleanup_twice():
    """Test that begin_cleanup cannot be called twice"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_before_cleanup(gtsi)
    gtsi.begin_cleanup()

    try:
        gtsi.begin_cleanup()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)


def test_begin_cleanup_without_cleanup():
    """Test that begin_cleanup cannot be called on test scenario without cleanup"""

    gtsi = build_generic_test_scenario_instance_without_cleanup()
    advance_new_gtsi_before_cleanup(gtsi)

    try:
        gtsi.begin_cleanup()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert "attempted to begin_cleanup, but no cleanup step is documented" in str(e)


def test_skip_cleanup():
    """Test the skip_cleanup base case"""

    gtsi = build_generic_test_scenario_instance_without_cleanup()

    # Test that we must run have called go_to_cleanup first
    try:
        gtsi.skip_cleanup()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_scenario(build_context())

    try:
        gtsi.skip_cleanup()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.go_to_cleanup()
    gtsi.skip_cleanup()


def test_skip_cleanup_twice():
    """Test the skip_cleanup cannot be called twice"""

    gtsi = build_generic_test_scenario_instance_without_cleanup()
    gtsi.begin_test_scenario(build_context())
    gtsi.go_to_cleanup()
    gtsi.skip_cleanup()

    try:
        gtsi.skip_cleanup()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)


def test_skip_cleanup_with_cleanup():
    """Test that skip_cleanup cannot be called on test scenario with cleanup"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_before_cleanup(gtsi)

    try:
        gtsi.skip_cleanup()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert "skipped cleanup even though a cleanup step is documented" in str(e)


def test_end_cleanup():
    """Test end_cleanup base case"""

    gtsi = _build_generic_test_scenario_instance()

    # Test that we must run have called begin_cleanup first
    try:
        gtsi.end_cleanup()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_scenario(build_context())

    try:
        gtsi.end_cleanup()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.go_to_cleanup()

    try:
        gtsi.end_cleanup()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_cleanup()
    gtsi.end_cleanup()


def test_end_cleanup_twice():
    """Test that we cannot call end_cleanup twice"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_before_cleanup(gtsi)
    gtsi.begin_cleanup()
    gtsi.end_cleanup()

    try:
        gtsi.end_cleanup()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)


def test_end_cleanup_and_skip_cleanup():
    """Test that end_cleanup cannot be called after skip_cleanup"""

    gtsi = build_generic_test_scenario_instance_without_cleanup()
    advance_new_gtsi_before_cleanup(gtsi)
    gtsi.skip_cleanup()

    try:
        gtsi.end_cleanup()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)


def test_ensure_cleanup_ended():
    """Test ensure_cleanup_ended base case"""

    gtsi = _build_generic_test_scenario_instance()

    # Test that we must run have called begin_cleanup first
    try:
        gtsi.ensure_cleanup_ended()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_scenario(build_context())

    try:
        gtsi.ensure_cleanup_ended()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.go_to_cleanup()

    try:
        gtsi.ensure_cleanup_ended()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_cleanup()
    gtsi.ensure_cleanup_ended()

    # Test that we can call ensure_cleanup_ended multiple times
    for _ in range(10):
        gtsi.ensure_cleanup_ended()


def test_ensure_cleanup_really_ends():
    """Test that ensure_cleanup_ended is indeed ending cleanup, meaning we cannot call end_cleanup anymore"""

    # Ensure first that case is working
    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_during_cleanup(gtsi)
    gtsi.end_cleanup()

    try:
        gtsi.end_cleanup()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    # Problematic case indicating that ensure_cleanup_ended called end_cleanup
    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_during_cleanup(gtsi)
    gtsi.ensure_cleanup_ended()

    try:
        gtsi.end_cleanup()
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)


def test_get_report_basic_data():
    """Test the report's base data returned by get_report"""

    # Test basic report data

    gtsi = _build_generic_test_scenario_instance()

    report = gtsi.get_report()

    assert report.name == "TestScenario"
    assert report.scenario_type == "scenarios.test.GenericTestScenarioForTests"
    assert report.documentation_url.endswith(
        "scenario_test/generic_test_scenario_test.md"
    )
    assert_date_is_close_to_now(report.start_time.datetime)
    assert report.resource_origins
    assert "test-resource" in report.resource_origins
    assert report.resource_origins["test-resource"] == "test-origin"


FINISHED_TEST_STEPS = [
    "nop",
    "begin_test_scenario",
    "begin_test_case",
    "begin_test_step",
    "end_test_step",
    "end_test_case",
    "end_test_scenario",
    "go_to_cleanup",
    "begin_cleanup",
    "end_cleanup",
]


def test_get_report_state_machine():
    """Test that Asking for the report before a test is done should result in an execution error"""

    steps = FINISHED_TEST_STEPS

    for steps_to_do in range(1, len(steps) + 1):
        gtsi = _build_generic_test_scenario_instance()
        run_a_set_of_calls_on_gtsi(gtsi, steps[:steps_to_do])

        report = gtsi.get_report()

        if "end_cleanup" in steps[:steps_to_do]:  # Meaning the scenario is done
            assert report.successful
            assert "execution_error" not in report
        else:
            assert not report.successful
            assert report.execution_error
            assert report.execution_error.type == "RuntimeError"
            assert (
                "when get_report was called (expected Complete)"
                in report.execution_error.message
            )


def test_record_execution_error():
    """Test the record_execution_error base case"""

    # Basic case: creating an exception should report it in the report

    gtsi = _build_generic_test_scenario_instance()
    gtsi.record_execution_error(ErrorForTests("test-exception"))

    report = gtsi.get_report()
    assert not report.successful
    assert report.execution_error
    assert report.execution_error.type.endswith(".ErrorForTests")
    assert report.execution_error.message == "test-exception"


def test_record_execution_error_twice():
    """It shouldn't be possible to call record_execution_error twice (since it will make the test complete)"""

    gtsi = _build_generic_test_scenario_instance()
    gtsi.record_execution_error(ErrorForTests("test-exception"))

    try:
        gtsi.record_execution_error(ErrorForTests("test-exception"))
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert (
            "indicated an execution error even though it was already Complete" in str(e)
        )


def test_record_execution_error_during_flow():
    """It should be possible to call record_execution_error at any point in time of the test, except when it's done"""

    steps = FINISHED_TEST_STEPS

    for steps_to_do in range(1, len(steps) + 1):
        gtsi = _build_generic_test_scenario_instance()
        run_a_set_of_calls_on_gtsi(gtsi, steps[:steps_to_do])

        if "end_cleanup" in steps[:steps_to_do]:  # Meaning the scenario is done
            try:
                gtsi.record_execution_error(ErrorForTests("test-exception"))
                assert False  # RuntimeError should have been called
            except RuntimeError as e:
                assert (
                    "indicated an execution error even though it was already Complete"
                    in str(e)
                )
        else:
            gtsi.record_execution_error(ErrorForTests("test-exception"))
            report = gtsi.get_report()

            assert not report.successful
            assert report.execution_error
            assert report.execution_error.type.endswith(".ErrorForTests")
            assert report.execution_error.message == "test-exception"


def test_get_report_return_cases_ran_no_cases():
    """Test that get_report return a report with cases that ran: case without cases"""

    # No test case
    gtsi = _build_generic_test_scenario_instance()
    gtsi.begin_test_scenario(build_context())
    terminate_gtsi_during_scenario(gtsi)

    report = gtsi.get_report()
    assert report.successful
    assert not report.cases


def test_get_report_return_cases_ran_one_cases():
    """Test that get_report return a report with cases that ran: case with 1 case"""

    # One test case
    gtsi = _build_generic_test_scenario_instance()
    gtsi.begin_test_scenario(build_context())
    gtsi.begin_test_case("test-case-1")
    gtsi.end_test_case()
    terminate_gtsi_during_scenario(gtsi)

    report = gtsi.get_report()
    assert report.successful
    assert report.cases
    names = [c.name for c in report.cases]
    assert "test-case-1" in names
    assert "test-case-2" not in names


def test_get_report_return_cases_ran_two_cases():
    """Test that get_report return a report with cases that ran: case with 2 cases"""

    # Two test case
    gtsi = _build_generic_test_scenario_instance()
    gtsi.begin_test_scenario(build_context())
    gtsi.begin_test_case("test-case-1")
    gtsi.end_test_case()
    gtsi.begin_test_case("test-case-2")
    gtsi.end_test_case()
    terminate_gtsi_during_scenario(gtsi)

    report = gtsi.get_report()
    assert report.successful
    assert report.cases
    names = [c.name for c in report.cases]
    assert "test-case-1" in names
    assert "test-case-2" in names


def test_get_report_return_test_case_data():
    """Test that get_report return a report with correct case data"""

    gtsi = _build_generic_test_scenario_instance()
    gtsi.begin_test_scenario(build_context())
    gtsi.begin_test_case("test-case-1")
    terminate_gtsi_during_case(gtsi)

    report = gtsi.get_report()
    case1 = report.cases[0]

    assert case1.name == "test-case-1"
    assert case1.documentation_url.endswith(
        "generic_test_scenario_test.md#test-case-1-test-case"
    )
    assert_date_is_close_to_now(case1.start_time.datetime)
    assert case1.end_time
    assert_date_is_close_to_now(case1.end_time.datetime)
    assert not case1.steps


def test_get_report_return_test_steps_data_1_steps():
    """Test that get_report return a report with steps that ran: case with one step"""

    gtsi = _build_generic_test_scenario_instance()
    gtsi.begin_test_scenario(build_context())
    gtsi.begin_test_case("test-case-1")
    gtsi.begin_test_step("test-step-1-1")
    terminate_gtsi_during_step(gtsi)

    report = gtsi.get_report()
    case1 = report.cases[0]
    assert case1.steps
    names = [s.name for s in case1.steps]
    assert "test-step-1-1" in names
    assert "test-step-1-2" not in names


def test_get_report_return_test_steps_data_2_steps():
    """Test that get_report return a report with steps that ran: case with two steps"""

    gtsi = _build_generic_test_scenario_instance()
    gtsi.begin_test_scenario(build_context())
    gtsi.begin_test_case("test-case-1")
    gtsi.begin_test_step("test-step-1-1")
    gtsi.end_test_step()
    gtsi.begin_test_step("test-step-1-2")
    terminate_gtsi_during_step(gtsi)

    report = gtsi.get_report()
    case1 = report.cases[0]
    assert case1.steps
    names = [s.name for s in case1.steps]
    assert "test-step-1-1" in names
    assert "test-step-1-2" in names


def test_get_report_return_test_step_data():
    """Test that get_report return a report with correct step data"""

    gtsi = _build_generic_test_scenario_instance()
    gtsi.begin_test_scenario(build_context())
    gtsi.begin_test_case("test-case-1")
    gtsi.begin_test_step("test-step-1-1")
    terminate_gtsi_during_step(gtsi)

    report = gtsi.get_report()
    case1 = report.cases[0]
    step1 = case1.steps[0]
    assert step1.name == "test-step-1-1"
    assert step1.documentation_url.endswith(
        "generic_test_scenario_test.md#test-step-1-1-test-step"
    )
    assert_date_is_close_to_now(step1.start_time.datetime)
    assert step1.end_time
    assert_date_is_close_to_now(step1.end_time.datetime)


def test_record_note_no_record():
    """Test the record_node function: case without nodes"""

    # No note send, no notes in the report
    gtsi = _build_generic_test_scenario_instance()
    report = gtsi.get_report()
    assert "notes" not in report


def test_record_note():
    """Test the record_node function: basic case"""
    gtsi = _build_generic_test_scenario_instance()
    with HideLogOutput():
        gtsi.record_note("test-key", "test-message")
    report = gtsi.get_report()

    assert "notes" in report
    assert report.notes
    assert "test-key" in report.notes
    assert report.notes["test-key"].message == "test-message"
    assert_date_is_close_to_now(report.notes["test-key"].timestamp.datetime)


def test_record_note_duplicate_keys():
    """Test the record_node function: duplicate key's report shouldn't be an issue with a new key generated"""

    gtsi = _build_generic_test_scenario_instance()
    with HideLogOutput():
        gtsi.record_note("test-key", "test-message")
        gtsi.record_note("test-key", "test-message-2")
        gtsi.record_note("test-key", "test-message-3")
    report = gtsi.get_report()

    assert "notes" in report
    assert report.notes
    # NB: We don't assume anything about keys
    assert len(report.notes.keys()) == 3
    messages = [r.message for r in report.notes.values()]
    assert "test-message" in messages
    assert "test-message-2" in messages
    assert "test-message-3" in messages


def test_record_note_state_machine():
    """It should be possible to call record_node at any point in time of the test, except when it's done"""

    steps = FINISHED_TEST_STEPS

    for steps_to_do in range(1, len(steps) + 1):
        gtsi = _build_generic_test_scenario_instance()
        run_a_set_of_calls_on_gtsi(gtsi, steps[:steps_to_do])

        with HideLogOutput():
            if "end_cleanup" in steps[:steps_to_do]:  # Meaning the scenario is done
                try:
                    gtsi.record_note("test-key", "test-message")
                    assert False  # RuntimeError should have been called
                except RuntimeError as e:
                    assert_runtime_is_state_error(e)
            else:
                gtsi.record_note("test-key", "test-message")


def test_record_query_working_in_case():
    """Test that record_query is working during a case running and not outside"""

    gtsi = _build_generic_test_scenario_instance()

    dummy_query = build_query()

    # Test that we must be in a step to record queriey
    try:
        gtsi.record_query(dummy_query)
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_scenario(build_context())

    try:
        gtsi.record_query(dummy_query)
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_case("test-case-1")

    try:
        gtsi.record_query(dummy_query)
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_step("test-step-1-1")
    gtsi.record_query(dummy_query)

    gtsi.end_test_step()
    try:
        gtsi.record_query(dummy_query)
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)


def test_record_query_working_in_cleanup():
    """Test that record_query is working during cleanup and not outside"""

    gtsi = _build_generic_test_scenario_instance()

    dummy_query = build_query()

    # Test that we must be in a step to record queriey
    try:
        gtsi.record_query(dummy_query)
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_scenario(build_context())

    try:
        gtsi.record_query(dummy_query)
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.go_to_cleanup()

    try:
        gtsi.record_query(dummy_query)
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_cleanup()
    gtsi.record_query(dummy_query)

    gtsi.end_cleanup()
    try:
        gtsi.record_query(dummy_query)
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)


def test_record_query_returned_in_step_no_queries():
    """Test that queries are recorded in steps: case without queries"""

    # No queries if record_query not called
    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_to_step(gtsi)
    terminate_gtsi_during_step(gtsi)

    report = gtsi.get_report()
    case1 = report.cases[0]
    step1 = case1.steps[0]

    assert "queries" not in step1


def test_record_query_returned_in_step_one_query():
    """Test that queries are recorded in steps: case with one query"""

    dummy_query = build_query()

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_to_step(gtsi)
    gtsi.record_query(dummy_query)
    terminate_gtsi_during_step(gtsi)

    report = gtsi.get_report()
    case1 = report.cases[0]
    step1 = case1.steps[0]

    assert "queries" in step1
    assert step1.queries
    assert len(step1.queries) == 1
    assert step1.queries[0] == dummy_query


def test_record_query_returned_in_step_two_queries():
    """Test that queries are recorded in steps: case with two queries"""
    dummy_query = build_query()
    dummy_query_2 = build_query()

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_to_step(gtsi)
    gtsi.record_query(dummy_query)
    gtsi.record_query(dummy_query_2)
    terminate_gtsi_during_step(gtsi)

    report = gtsi.get_report()
    case1 = report.cases[0]
    step1 = case1.steps[0]

    assert "queries" in step1
    assert step1.queries
    assert len(step1.queries) == 2
    assert step1.queries[0] == dummy_query
    assert step1.queries[1] == dummy_query_2


def test_record_query_only_one():
    """Test that record query is only recording once identical queries"""

    dummy_query = build_query()

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_to_step(gtsi)
    with HideLogOutput():
        gtsi.record_query(dummy_query)
        gtsi.record_query(dummy_query)
    terminate_gtsi_during_step(gtsi)

    report = gtsi.get_report()
    case1 = report.cases[0]
    step1 = case1.steps[0]

    assert step1.queries
    assert len(step1.queries) == 1
    assert step1.queries[0] == dummy_query


def test_record_queries():
    """Test record_queries base case"""

    dummy_query = build_query()
    dummy_query_2 = build_query()

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_to_step(gtsi)
    gtsi.record_queries([dummy_query, dummy_query_2])
    terminate_gtsi_during_step(gtsi)

    report = gtsi.get_report()
    case1 = report.cases[0]
    step1 = case1.steps[0]

    assert step1.queries
    assert len(step1.queries) == 2


def test_record_queries_duplicates():
    """Test record_queries don't record duplicates"""

    dummy_query = build_query()

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_to_step(gtsi)
    with HideLogOutput():
        gtsi.record_queries([dummy_query, dummy_query])
    terminate_gtsi_during_step(gtsi)

    report = gtsi.get_report()
    case1 = report.cases[0]
    step1 = case1.steps[0]

    assert step1.queries
    assert len(step1.queries) == 1


def test_check_working_in_case():
    """Test that check() are working in test steps (and not around)"""

    gtsi = _build_generic_test_scenario_instance()

    # Test that we must be in a step to record queriey
    try:
        gtsi.check("test-check-1-1-1")
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_scenario(build_context())

    try:
        gtsi.check("test-check-1-1-1")
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_case("test-case-1")

    try:
        gtsi.check("test-check-1-1-1")
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_step("test-step-1-1")
    gtsi.check("test-check-1-1-1")

    gtsi.end_test_step()
    try:
        gtsi.check("test-check-1-1-1")
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)


def test_check_working_in_cleanup():
    """Test that check() are working in cleanup's steps (and not around)"""

    gtsi = _build_generic_test_scenario_instance()

    # Test that we must be in a step to record queriey
    try:
        gtsi.check("test-check-c-1")
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_test_scenario(build_context())

    try:
        gtsi.check("test-check-c-1")
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.go_to_cleanup()

    try:
        gtsi.check("test-check-c-1")
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)

    gtsi.begin_cleanup()
    gtsi.check("test-check-c-1")

    gtsi.end_cleanup()
    try:
        gtsi.check("test-check-c-1")
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert_runtime_is_state_error(e)


def test_check_unavailable():
    """Test that check is not working with unknown checks"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_to_step(gtsi)
    gtsi.check("test-check-1-1-1")

    try:
        gtsi.check("not-a-check")
        assert False  # RuntimeError should have been called
    except RuntimeError as e:
        assert "but that check is not declared in documentation" in str(e)


def test_check_unavailable_but_allowed():
    """Test that check is working with unknown checks when the special flag used for unit test is enabled"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_to_step(gtsi)
    gtsi._allow_undocumented_checks = True
    gtsi.check("not-a-check")


def test_check_is_recored():
    """Test that check result are reported in the report"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_to_step(gtsi)
    check = gtsi.check("test-check-1-1-1")
    check.record_passed()
    terminate_gtsi_during_step(gtsi)

    report = gtsi.get_report()
    case1 = report.cases[0]
    step1 = case1.steps[0]

    assert step1.passed_checks
    assert len(step1.passed_checks) == 1
    assert step1.passed_checks[0].name == "test-check-1-1-1"
    assert_date_is_close_to_now(step1.passed_checks[0].timestamp.datetime)


def test_check_no_participants():
    """Test that check participants are reported in the report: case without participants"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_to_step(gtsi)
    with gtsi.check("test-check-1-1-1") as check:
        check.record_passed()
    terminate_gtsi_during_step(gtsi)

    report = gtsi.get_report()
    case1 = report.cases[0]
    step1 = case1.steps[0]
    check = step1.passed_checks[0]

    assert len(check.participants) == 0


def test_check_normal_participants():
    """Test that check participants are reported in the report: base case"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_to_step(gtsi)
    with gtsi.check("test-check-1-1-1", ["42", "24"]) as check:
        check.record_passed()
    terminate_gtsi_during_step(gtsi)

    report = gtsi.get_report()
    case1 = report.cases[0]
    step1 = case1.steps[0]
    check = step1.passed_checks[0]

    assert check.participants == ["42", "24"]


def test_check_participant_allow_string():
    """Test that check participants with a simple string is allowed and converted to the expect list"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_to_step(gtsi)
    with gtsi.check("test-check-1-1-1", "42") as check:
        check.record_passed()
    terminate_gtsi_during_step(gtsi)

    report = gtsi.get_report()
    case1 = report.cases[0]
    step1 = case1.steps[0]
    check = step1.passed_checks[0]

    assert check.participants == ["42"]


def test_on_failled_check_called():
    """Test that the on_failed_check callback is called when check are failling"""

    has_been_called_with_check_result = None

    def callme(check):
        nonlocal has_been_called_with_check_result
        has_been_called_with_check_result = check

    gtsi = _build_generic_test_scenario_instance()
    gtsi.on_failed_check = callme
    advance_new_gtsi_to_step(gtsi)
    with gtsi.check("test-check-1-1-2-low") as check:
        check.record_failed("")
        assert has_been_called_with_check_result
        assert has_been_called_with_check_result.name == "test-check-1-1-2-low"


def test_stop_fast_disabled():
    """Test that wanted excpetions are raised when stop fast is disabled, on high and Ccitical levels"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_to_step(gtsi)

    with gtsi.check("test-check-1-1-2-low") as check:
        check.record_failed("")
    with gtsi.check("test-check-1-1-3-medium") as check:
        check.record_failed("")
    try:
        with gtsi.check("test-check-1-1-4-high") as check:
            check.record_failed("")
        assert False  # ScenarioCannotContinueError should have been raised
    except ScenarioCannotContinueError:
        pass
    try:
        with gtsi.check("test-check-1-1-5-critical") as check:
            check.record_failed("")
            assert False  # TestRunCannotContinueError should have been raised
    except _TestRunCannotContinueError:
        pass


def test_stop_fast_enabled():
    """Test that wanted excpetions are raised when stop fast is enabled, on all levels but low"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_to_step(gtsi)

    gtsi = _build_generic_test_scenario_instance()
    c = build_context(stop_fast=True)
    gtsi.begin_test_scenario(c)
    gtsi.begin_test_case("test-case-1")
    gtsi.begin_test_step("test-step-1-1")

    with HideLogOutput():
        with gtsi.check("test-check-1-1-2-low") as check:
            check.record_failed("")
        try:
            with gtsi.check("test-check-1-1-3-medium") as check:
                check.record_failed("")
                assert False  # TestRunCannotContinueError should have been raised
        except _TestRunCannotContinueError:
            pass
        try:
            with gtsi.check("test-check-1-1-4-high") as check:
                check.record_failed("")
            assert False  # _TestRunCannotContinueError should have been raised
        except _TestRunCannotContinueError:
            pass
        try:
            with gtsi.check("test-check-1-1-5-critical") as check:
                check.record_failed("")
                assert False  # TestRunCannotContinueError should have been raised
        except _TestRunCannotContinueError:
            pass


def test_report_status_should_be_ok_if_low_failled():
    """Test report status should be maked as successfull if a low check failled"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_to_step(gtsi)
    with gtsi.check("test-check-1-1-2-low") as check:
        check.record_failed("")
    terminate_gtsi_during_step(gtsi)

    report = gtsi.get_report()

    assert report.successful


def test_report_status_should_be_unsuccessfull_if_medium_failled():
    """Test report status should be maked as unsuccessfull if a medium check failled"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_to_step(gtsi)
    with gtsi.check("test-check-1-1-3-medium") as check:
        check.record_failed("")
    terminate_gtsi_during_step(gtsi)

    report = gtsi.get_report()

    assert not report.successful


def test_report_status_should_be_unsuccessfull_if_high_failled():
    """Test report status should be maked as unsuccessfull if a high check failled"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_to_step(gtsi)
    try:
        with gtsi.check("test-check-1-1-4-high") as check:
            check.record_failed("")
            assert False  # ScenarioCannotContinueError should have been raised
    except ScenarioCannotContinueError:
        pass
    terminate_gtsi_during_step(gtsi)

    report = gtsi.get_report()

    assert not report.successful


def test_report_status_should_be_unsuccessfull_if_critical_failled():
    """Test report status should be maked as unsuccessfull if a critical check failled"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_to_step(gtsi)
    try:
        with gtsi.check("test-check-1-1-5-critical") as check:
            check.record_failed("")
            assert False  # TestRunCannotContinueError should have been raised
    except _TestRunCannotContinueError:
        pass
    terminate_gtsi_during_step(gtsi)

    report = gtsi.get_report()

    assert not report.successful


def test_report_status_should_be_ok_if_low_failled_in_cleanup():
    """Test report status should be maked as successfull if a low check failled during cleanup"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_during_cleanup(gtsi)
    with gtsi.check("test-check-c-2-low") as check:
        check.record_failed("")
    gtsi.end_cleanup()

    report = gtsi.get_report()

    assert report.successful


def test_report_status_should_be_unsuccessfull_if_medium_failled_in_cleanup():
    """Test report status should be maked as unsuccessfull if a medium check failled during cleanup"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_during_cleanup(gtsi)
    with gtsi.check("test-check-c-3-medium") as check:
        check.record_failed("")
    gtsi.end_cleanup()

    report = gtsi.get_report()

    assert not report.successful


def test_report_status_should_be_unsuccessfull_if_high_failled_in_cleanup():
    """Test report status should be maked as unsuccessfull if a high check failled during cleanup"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_during_cleanup(gtsi)
    try:
        with gtsi.check("test-check-c-4-high") as check:
            check.record_failed("")
            assert False  # ScenarioCannotContinueError should have been raised
    except ScenarioCannotContinueError:
        pass
    gtsi.end_cleanup()

    report = gtsi.get_report()

    assert not report.successful


def test_report_status_should_be_unsuccessfull_if_critical_failled_in_cleanup():
    """Test report status should be maked as unsuccessfull if a critical check failled during cleanup"""

    gtsi = _build_generic_test_scenario_instance()
    advance_new_gtsi_during_cleanup(gtsi)
    try:
        with gtsi.check("test-check-c-5-critical") as check:
            check.record_failed("")
            assert False  # TestRunCannotContinueError should have been raised
    except _TestRunCannotContinueError:
        pass
    gtsi.end_cleanup()

    report = gtsi.get_report()

    assert not report.successful


# TODO Ensure unkown participan or query type is tested in record query
