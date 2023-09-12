from typing import List, Union

from implicitdict import ImplicitDict
from monitoring.uss_qualifier.action_generators.action_generator import (
    action_generator_type_from_name,
    action_generator_specification_type,
)
from monitoring.uss_qualifier.action_generators.definitions import (
    ActionGeneratorDefinition,
)
from monitoring.uss_qualifier.action_generators.documentation.definitions import (
    PotentialGeneratedAction,
    PotentialTestScenarioAction,
    PotentialTestSuiteAction,
    PotentialActionGeneratorAction,
)
from monitoring.uss_qualifier.suites.definitions import (
    TestSuiteActionDeclaration,
    ActionType,
)


def list_potential_actions_for_action_generator_definition(
    generator_def: Union[ActionGeneratorDefinition, PotentialActionGeneratorAction]
) -> List[PotentialGeneratedAction]:
    action_generator_type = action_generator_type_from_name(
        generator_def.generator_type
    )
    specification_type = action_generator_specification_type(action_generator_type)
    if specification_type is not None:
        spec = ImplicitDict.parse(generator_def.specification, specification_type)
    else:
        spec = None
    return action_generator_type.list_potential_actions(spec)


def list_potential_actions_for_action_declaration(
    declaration: TestSuiteActionDeclaration,
) -> List[PotentialGeneratedAction]:
    action_type = declaration.get_action_type()
    if action_type == ActionType.TestScenario:
        return [
            PotentialGeneratedAction(
                test_scenario=PotentialTestScenarioAction(
                    scenario_type=declaration.test_scenario.scenario_type
                )
            )
        ]
    elif action_type == ActionType.TestSuite:
        if "suite_type" in declaration.test_suite and declaration.test_suite.suite_type:
            return [
                PotentialGeneratedAction(
                    test_suite=PotentialTestSuiteAction(
                        suite_type=declaration.test_suite.suite_type
                    )
                )
            ]
        elif (
            "suite_definition" in declaration.test_suite
            and declaration.test_suite.suite_definition
        ):
            return [
                PotentialGeneratedAction(
                    test_suite=PotentialTestSuiteAction(
                        suite_definition=declaration.test_suite.suite_definition
                    )
                )
            ]
    elif action_type == ActionType.ActionGenerator:
        return [
            PotentialGeneratedAction(
                action_generator=PotentialActionGeneratorAction(
                    generator_type=declaration.action_generator.generator_type
                )
            )
        ]
    else:
        raise NotImplementedError(f"Action type {action_type} is not supported")
