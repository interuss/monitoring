from monitoring.uss_qualifier.scenarios.scenario import TestScenario as _TestScenario
from monitoring.uss_qualifier.scenarios.scenario import (
    find_test_scenarios,
    get_scenario_type_by_name,
    get_scenario_type_name,
)

from .utils import InjectFakeScenariosModule, build_fake_scenarios_module


def test_get_scenario_type_by_name():
    """Test the get_scenario_type_by_name function, retrieving various mock TestScenarios by name and ensuring invalid or non-existing classes are returning errors"""

    with InjectFakeScenariosModule() as fake_module:
        assert (
            get_scenario_type_by_name("scenarios.test.TestScenarioA")
            == fake_module.TestScenarioA
        )

        try:
            get_scenario_type_by_name("scenarios.test.NotATestScenarioC")
            assert (
                False
            )  # NotImplementedError should have been raised (not a TestScenario)
        except NotImplementedError:
            pass

        try:
            get_scenario_type_by_name("scenarios.test.ThisClassDoesntExists")
            assert False  # NotImplementedError should have been raised
        except ValueError:
            pass


def test_get_scenario_type_name():
    """Test get_scenario_type_name function, by comparing result of known mock classes and that non-valid classes types or classes outside of expected modules are returning errors"""

    fake_module = build_fake_scenarios_module()

    assert (
        get_scenario_type_name(fake_module.TestScenarioA)
        == "scenarios.scenario_test.utils.build_fake_scenarios_module.<locals>.TestScenarioA"
    )
    assert (
        get_scenario_type_name(fake_module.submodule.TestScenarioSubA)
        == "scenarios.scenario_test.utils.build_fake_scenarios_module.<locals>.TestScenarioSubA"
    )

    try:
        get_scenario_type_name(fake_module.NotATestScenarioC)
        assert False  # ValueError should have been raised
    except ValueError:
        pass

    class OutsideTest(_TestScenario):
        __module__ = "outside"

    try:
        get_scenario_type_name(OutsideTest)
        assert False  # ValueError should have been raised
    except ValueError:
        pass


def test_find_test_scenarios():
    """Test find_test_scenarios by using a mock module with various test cases."""

    fake_module = build_fake_scenarios_module()

    result = find_test_scenarios(fake_module)

    classes_names = [c.__name__ for c in result]

    # Ensure base system is working and the TestScenarioA is detected
    assert "TestScenarioA" in classes_names
    assert "TestScenarioB" in classes_names

    # Ensure non-test scenarios are not returned
    assert "NotATestScenarioC" not in classes_names

    # Ensure sub modules classes are also detected
    assert "TestScenarioSubA" in classes_names
    assert "TestScenarioSubB" in classes_names

    # Ensure sub modules of submodules are also detected
    assert "TestScenarioSubSubA" in classes_names

    # Ensure classes are returned only once (TestScenarioB is set in two
    # modules
    assert classes_names.count("TestScenarioB") == 1

    # Ensure classes are sorted
    assert sorted(classes_names) == classes_names


def test_find_test_scenarios_already_checked():
    """Test find_test_scenarios already_checked argument by using a mock module with various test cases."""

    fake_module = build_fake_scenarios_module()

    # Use already_checked argument to ignore submodules
    result = find_test_scenarios(
        fake_module,
        {
            "monitoring.uss_qualifier.scenarios.test.submodule",
        },
    )
    classes_names = [c.__name__ for c in result]

    # Top level classes should be there
    assert "TestScenarioA" in classes_names
    assert "TestScenarioB" in classes_names

    # Sub modules classes and sub-sub modules shouldn't be there, because there
    # where in the already_checked parameter
    assert "TestScenarioSubA" not in classes_names
    assert "TestScenarioSubB" not in classes_names
    assert "TestScenarioSubSubA" not in classes_names
