from __future__ import annotations

import inspect
from typing import List

from loguru import logger

from monitoring.monitorlib.inspection import fullname
from monitoring.uss_qualifier.requirements.documentation import get_requirement
from monitoring.uss_qualifier.scenarios.documentation.autoformat import (
    format_scenario_documentation,
)
from monitoring.uss_qualifier.scenarios.documentation.definitions import TestCheckTree
from monitoring.uss_qualifier.scenarios.documentation.parsing import (
    RESOURCES_HEADING,
    get_documentation,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenarioType


def validate(test_scenarios: List[TestScenarioType]):
    checks_without_severity = TestCheckTree(scenarios={})

    for test_scenario in test_scenarios:
        # Verify that documentation parses
        docs = get_documentation(test_scenario)

        # Verify that all requirements are documented
        for case in docs.cases:
            for step in case.steps:
                for check in step.checks:
                    for req in check.applicable_requirements:
                        try:
                            get_requirement(req)
                        except ValueError as e:
                            raise ValueError(
                                f"In {fullname(test_scenario)} documentation, test case '{case.name}', test step '{step.name}', check '{check.name}': {str(e)}"
                            )

        # Verify that all resources are documented
        constructor_signature = inspect.signature(test_scenario.__init__)
        args = []
        for arg_name, arg in constructor_signature.parameters.items():
            if arg_name == "self":
                continue
            if "resources" not in docs:
                raise ValueError(
                    f'Test scenario {fullname(test_scenario)} declares resources in its constructor, but there is no "{RESOURCES_HEADING}" section in its documentation'
                )
            if arg_name not in docs.resources:
                raise ValueError(
                    f"Test scenario {fullname(test_scenario)} declares resource {arg_name} ({fullname(arg.annotation)}), but this resource is not documented"
                )
            args.append(arg_name)
        for documented_resource in docs.resources:
            if documented_resource not in args:
                raise ValueError(
                    f"Documentation for test scenario {fullname(test_scenario)} specifies a resource named {documented_resource}, but this resource is not declared as a resource in the constructor"
                )

        # Identify all checks without documented severity
        for case in docs.cases:
            for step in case.steps:
                for check in step.checks:
                    if "severity" not in check or check.severity is None:
                        checks_without_severity.add_check(
                            scenario=test_scenario, case=case, step=step, check=check
                        )

    # Verify that no automatic formatting is necessary
    changes = format_scenario_documentation(test_scenarios)
    if changes:
        file_list = ", ".join(c for c in changes)
        raise ValueError(
            f"{len(changes)} documentation files need to be auto-formatted; run `make format` to perform this operation automatically (files to be reformatted: {file_list}"
        )

    # Print out number of test checks that don't yet have severity annotations in documentation
    logger.warning(
        f"{checks_without_severity.n} checks without severity annotated in documentation"
    )

    # Verify that no new checks without documented severity were added
    preexisting_checks_without_severity = TestCheckTree.preexisting(
        "checks_without_severity.json"
    )
    new_checks_without_severity = checks_without_severity.without(
        preexisting_checks_without_severity
    )
    if new_checks_without_severity.n > 0:
        raise ValueError(
            f"{new_checks_without_severity.n} new checks added without severity indicated in documentation:\n{new_checks_without_severity.render()}"
        )

    # Verify that checks without documented severity are up to date
    removed_checks_without_severity = preexisting_checks_without_severity.without(
        checks_without_severity
    )
    if removed_checks_without_severity.n > 0:
        raise ValueError(
            f"{removed_checks_without_severity.n} checks without severity indicated in documentation have been removed (great!); run `make format` to update tracking."
        )
