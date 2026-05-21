# AI Agent Collaboration Guide

This document contains key context, nuances, and troubleshooting tips specifically designed to help AI agents (and human developers) quickly understand and contribute to this repository, avoiding common pitfalls.

## 1. Project Dependencies and Environment
- **Environment**: This project primarily uses [uv](https://docs.astral.sh/uv/) for dependency management and locking.
- **External Schemas**: Many UTM standards implementations (such as the ASTM F3548 schemas) are provided by the external `uas_standards` package instead of living directly within the local `./monitoring` or `./schemas` directories.
- **Agent Tip**: Since external packages reside in the virtual environment, you cannot explore them directly with standard local file `grep` searches. To inspect an external schema's properties (e.g., `OperationalIntentReference`), it is much faster to run a Python introspection script through `uv`:
  ```bash
  uv run python -c "from uas_standards.astm.f3548.v21.api import OperationalIntentReference; print(OperationalIntentReference.__annotations__)"
  ```

## 2. Navigating Data Schemas
- **Implicit Types**: Many schema objects inherit from `ImplicitDict`. This means that reading their raw Python class definitions may not reveal all their expected structure. Rely on their `__annotations__` or their OpenAPI documentation.
- **Hidden Schema Nuances**: Certain F3548 properties intuitively behave differently than standard logic might predict (e.g., F3548's `OperationalIntentReference` does *not* represent 4D `altitude` extents, whereas `Volume4D` details do). Always verify property existence programmatically instead of relying on assumptions.
- **Datetime Types**: Fields annotated as `StringBasedDateTime` (or generic `Time` structures wrapping it) inherently expose a `.datetime` property mapping directly to Python's built-in `datetime.datetime` type. Always rely on this `.datetime` attribute for date-math instead of manually parsing string strings.

## 3. `uss_qualifier` Test Development Rules
- **Markdown Documentation is Mandatory**: Every check (e.g., `self._scenario.check(...)`) added to a Python test scenario must be meticulously documented in the corresponding Markdown documentation file for that specific test scenario or fragment.
- **Documentation Traceability**: All documented test checks must trace back to exactly one or more requirements using a specific bold format, and feature a severity emoji prefix (e.g., `## 🛑 Correct operational intent details check`). You must refer to `monitoring/uss_qualifier/scenarios/README.md` for specific markup details before modifying test steps.

## 4. Local Testing constraints
- **Docker Dependency**: Mock USS and DSS environments require active Docker containers. Standard testing commands are typically structured via bash scripts like `./monitoring/uss_qualifier/run_locally.sh <config>`. If container-building fails due to `Authentication` or package registry issues in the agent's environment, gracefully halt and ask the human user to run the script instead.

## 5. Continuous Improvement of this Guide
- **Pay It Forward**: As an AI agent, your ability to acquire context quickly is critical. If, during your work, you find yourself spending significant time overcoming a misunderstanding, discovering a hidden project nuance, or writing introspection scripts to understand a schema, **please proactively update this `AGENTS.md` file**. Add concise tips or warnings to help future agents (including yourself) avoid the same friction, alongside completing your core task.
- **Correcting Mistakes**: Documentation can become outdated or contain errors over time. If your core work reveals that information in this `AGENTS.md` file is mistaken or missing critical context, please take the initiative to fix those errors while completing your primary objectives!
