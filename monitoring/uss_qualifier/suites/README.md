# USS Qualifier test suites

A test suite is a set of tests that establish compliance to the thing they're named after; it may be thought of as a "playlist" of test scenarios.  Example: Passing the "ASTM F3548-21" test suite should indicate the systems under test are compliant with ASTM F3548-21.

A test suite is composed of a list of actions, each one being a [test scenario](../scenarios/README.md), [action generator](../action_generators/README.md), or another test suite.  Each action on the list is executed sequentially.

A test suite is defined with a YAML file following the [`TestSuiteDefinition` schema](definitions.py).

Test suites are tolerant of incomplete resources available for an action.  All resources declared as required for the test suite must be provided, but some resources may be marked as optional (by suffixing the resource type name with `?`) and those resources do not need to be provided to the test suite.  If an optional resource is used as input to a test suite action ([scenario](../scenarios/README.md), child test suite, or [action generator](../action_generators/README.md)) that requires that resource but the resource was not provided to the parent test suite, that test suite action will be skipped and this will be noted in the test report, but the remaining test suite actions will be executed normally.

## Documentation

Test suite documentation is generated automatically; use `make format` from the repository root to regenerate it.

### Actions

This section of a test suite documentation page summarizes the actions that will be taken when the test suite is run.

### Checked requirements

This section of a test suite documentation page summarizes the requirements the suite may be capable of checking.  A requirement is "checked" if there is [a declared test check](../scenarios/README.md#checks) with [documentation](../scenarios/README.md#test-checks) indicating that a failure of that check would imply a failure of the requirement.  A particular test run may not perform all potential checks.  For instance, if a test step is performed only in certain situations (e.g., a provided resource has certain characteristics) and skipped otherwise, then the checks associated with that test step will not be performed in that test run.  All checks that are performed will be recorded in the report as passed or failed.

The columns of the table in this section are as follows:

#### Package

All [requirements defined in this monitoring repository](../requirements/README.md) are defined exactly once in a particular "package" (InterUSS organizational structure to keep track of requirements) which represents the canonical source of that requirement.  This column specifies and links to the package in which the requirement is defined in this monitoring repository.

#### Requirement

This column contains the name of the requirement in the [package](#package) namespace.  Since periods are not allowed in requirement names, when InterUSS finds it helpful to refer to a particular portion of a named requirement, the name and portion(s) are usually delimited with commas.  For instance, if a document specified REQ003 and that requirement had three distinct parts (a, b, and c), one requirement name might be `REQ003,a`.

#### Status

Test check documentation may include a `TODO:` note indicating that the check (and perhaps the containing test step) has not been fully implemented.  If there is no such note for any of the checks relevant to this requirement, this column will indicate "Implemented".  If all checks relevant to this requirement have this indication, this column will indicate "TODO".  If some checks have this indication and others do not, this column will indicate "Implemented + TODO".  A requirement is only listed in this table if the test suite may cause a check to happen that is associated with that requirement.

#### Checked in

This column includes a list of test scenarios containing checks associated with the corresponding requirement.  Only test scenarios that may be run as part of the test suite are included.
