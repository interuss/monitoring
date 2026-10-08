import pytest

from monitoring.uss_qualifier.action_generators.documentation.definitions import (
    PotentialGeneratedAction,
)
from monitoring.uss_qualifier.reports.tested_requirements.breakdown import (
    _populate_breakdown_with_action_declaration,
)
from monitoring.uss_qualifier.reports.tested_requirements.data_types import (
    TestedBreakdown as Breakdown,
)
from monitoring.uss_qualifier.suites.documentation.documentation import (
    TestSuiteRenderContext as RenderContext,
)
from monitoring.uss_qualifier.suites.documentation.documentation import (
    _collect_requirements_from_action,
    _render_action,
)


@pytest.mark.parametrize("consumer", ["render", "requirements", "breakdown"])
# This test is AI-generated and has not been closely inspected by a human.
def test_invalid_generated_action_reports_value_error(consumer: str):
    action = PotentialGeneratedAction()
    with pytest.raises(ValueError, match="Invalid PotentialGeneratedAction"):
        if consumer == "render":
            _render_action(
                action,
                RenderContext("suite.yaml", "suite.md", ".", 0, 0, {}),
            )
        elif consumer == "requirements":
            _collect_requirements_from_action(action)
        else:
            _populate_breakdown_with_action_declaration(
                Breakdown(packages=[]), action, [], None
            )
