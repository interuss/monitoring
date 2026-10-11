# AI Agent Collaboration Guide

This document contains key context, nuances, and troubleshooting tips specifically designed to help AI agents (and human developers) quickly understand and contribute to this repository, avoiding common pitfalls.

## 1. Project Dependencies and Environment
- **Environment**: This project primarily uses [uv](https://docs.astral.sh/uv/) for dependency management and locking.
- **External Schemas**: Many UTM standards implementations (such as the ASTM F3548 schemas) are provided by the external `uas_standards` package instead of living directly within the local `./monitoring` or `./schemas` directories.
- **Agent Tip**: Since external packages reside in the virtual environment, you cannot explore them directly with standard local file `grep` searches. To inspect an external schema's properties (e.g., `OperationalIntentReference`), it is much faster to run a Python introspection script through `uv`:
  ```bash
  uv run python -c "from uas_standards.astm.f3548.v21.api import OperationalIntentReference; print(OperationalIntentReference.__annotations__)"
  ```
- **uv run Troubleshooting**: If running commands via `uv run` fails due to multi-platform dependency resolution issues (e.g. missing upload dates/wheels in custom package registries), you can force it to use standard PyPI by specifying the `--index` option:
  ```bash
  PYTHONPATH=. uv run --index https://pypi.org/simple pytest monitoring/uss_qualifier/reports/obfuscation_test.py
  ```
- **Linter and Formatting**: To verify stylistic correctness/consistency in the monitoring project, run `make format` (to auto-format when possible) or `make lint` (to check correctness/type check) from the root of the `monitoring` directory. Do not run `ruff` or `basedpyright` directly if they fail due to environment/index configuration issues.
- **Jsonnet `native_callbacks` Parameter Names**: In `_jsonnet` (`jsonnet` v0.22.0), parameter names in the `native_callbacks` tuple passed to `_jsonnet.evaluate_snippet` **must be single-character ASCII strings** (e.g., `("y", "x", "l")` instead of `("lat", "lng", "level")`). Due to a use-after-free bug in `_jsonnet`'s C extension (`handle_native_callbacks`; see [google/jsonnet#1321](https://github.com/google/jsonnet/issues/1321) and [google/jsonnet#1333](https://github.com/google/jsonnet/pull/1333)), multi-byte `PyBytes` objects returned by `PyUnicode_AsUTF8String` are prematurely `Py_DECREF`ed and freed inside the parameter loop before `jsonnet_native_callback` is called, causing subsequent parameter strings to reuse the same memory address and fail at runtime with `RUNTIME ERROR: binding parameter a second time: <param>`. Single-byte `PyBytes` objects are immortal singletons in CPython and are not freed.


## 2. Navigating Data Schemas
- **Implicit Types**: Many schema objects inherit from `ImplicitDict`. This means that reading their raw Python class definitions may not reveal all their expected structure. Rely on their `__annotations__` or their OpenAPI documentation.
- **Optional `ImplicitDict` Fields**: `ImplicitDict` fields annotated with `| None` (or `Optional[...]`) indicate optional dictionary keys. In implicitdict 5.0.0, accessing a missing optional attribute returns `None` without inserting a key; use `"field" in obj` to distinguish absence from an explicitly stored null. Constructor keyword arguments set to `None` normally omit optional values, but class defaults may still populate the key; assigning `obj.field = None` or `obj["field"] = None` stores an explicit null. Use dictionary membership rather than `hasattr` when key presence matters.
- **implicitdict 5.0.0 Typing**: Its unannotated `__getattribute__` introduces `None` into the inferred type of undeclared attributes (`Unknown | Any | None` in basedpyright 1.40.1), while declared fields and properties retain their types. New optional-access diagnostics may expose a nonexistent member or the wrong schema class rather than a missing optional value. Check the receiver's declaration before adding a None guard or suppressing the diagnostic. An explicit `-> Any` return annotation on the accessor restores the previous permissive fallback without changing runtime behavior, but also hides these pre-existing member-access mistakes.
- **Hidden Schema Nuances**: Certain F3548 properties intuitively behave differently than standard logic might predict (e.g., F3548's `OperationalIntentReference` does *not* represent 4D `altitude` extents, whereas `Volume4D` details do). Always verify property existence programmatically instead of relying on assumptions.
- **Datetime Types**: Fields annotated as `StringBasedDateTime` (or generic `Time` structures wrapping it) inherently expose a `.datetime` property mapping directly to Python's built-in `datetime.datetime` type. Always rely on this `.datetime` attribute for date-math instead of manually parsing string strings.
- **DSS Base URL Suffixes**: When configuring DSS instances, the base URL for ASTM F3411-22a (NetRID v2) requires the `/rid/v2` suffix path (e.g. `http://dss1.uss1.localutm/rid/v2`), whereas F3411-19 and SCD (F3548) typically use the host base URL directly without that suffix.

## 3. `uss_qualifier` Test Development Rules
- **Markdown Documentation is Mandatory**: Every check (e.g., `self._scenario.check(...)`) added to a Python test scenario must be meticulously documented in the corresponding Markdown documentation file for that specific test scenario or fragment.
- **Documentation Traceability**: All documented test checks must trace back to exactly one or more requirements using a specific bold format, and feature a severity emoji prefix (e.g., `## 🛑 Correct operational intent details check`). You must refer to `monitoring/uss_qualifier/scenarios/README.md` for specific markup details before modifying test steps.

## 4. Local Testing constraints
- **Qualifier Working Directory**: Run resource-construction checks and qualifier resource tests from `monitoring/uss_qualifier` with the repository root on `PYTHONPATH`. External resource paths such as `file://./test_data/...` resolve relative to the current working directory, as they do in `run_locally.sh`.
- **Docker Dependency**: Mock USS and DSS environments require active Docker containers. Standard testing commands are typically structured via bash scripts like `./monitoring/uss_qualifier/run_locally.sh <config>`. If container-building fails due to `Authentication` or package registry issues in the agent's environment, gracefully halt and ask the human user to run the script instead.

## 5. Continuous Improvement of this Guide
- **Pay It Forward**: As an AI agent, your ability to acquire context quickly is critical. If, during your work, you find yourself spending significant time overcoming a misunderstanding, discovering a hidden project nuance, or writing introspection scripts to understand a schema, **please proactively update this `AGENTS.md` file**. Add concise tips or warnings to help future agents (including yourself) avoid the same friction, alongside completing your core task.
- **Correcting Mistakes**: Documentation can become outdated or contain errors over time. If your core work reveals that information in this `AGENTS.md` file is mistaken or missing critical context, please take the initiative to fix those errors while completing your primary objectives!

## 6. Agent Annotations
- **Tagging Unit Tests**: When creating new unit tests, please tag each new test with the comment `# This test is AI-generated and has not been closely inspected by a human.` above the test definition (one comment per test_* function).  Your user may remove this annotation if they closely inspect it, but this is not generally necessary and pull requests should not generally be rejected because of these annotations.
