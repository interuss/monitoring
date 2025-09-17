# Sequence view artifact

## Purpose

A sequence view artifact is intended to show a chronological view of what
happened during a test run.  It is mostly useful to developers trying to
understand the context of a test failure or examine the sequence of events
for a test run.

## Overview

The generated index file contains a list of scenarios and what caused them
to be run (e.g., test suite, action generator, etc).  Each scenario's page
details the events (queries, checks, notes) that occurred during the
execution of that scenario.

## Index page

The index page contains a brief summary of test run metadata at the top in a table, followed by collapsed configuration details, followed by a "Scenarios executed" table.

### Resources configuration

The "Resources configuration" section presents the resources components of the test configuration arranged by "Baseline" and "Environment".  This is intended to be useful when trying to understand what the test baseline consists of, and what the test environment consists of.

### Full configuration

The "Full configuration" section presents the full, literal test configuration in a mostly raw form.  It can be somewhat harder to read/understand than the "Resources configuration" view if looking only for resources, but it more directly corresponds to the actual instructions provided to uss_qualifier and contains all configuration elements (not just resources).

### Scenarios executed

The "Scenarios executed" table shows how test scenarios came to be run (e.g., test suite A included action generator B which ran test suite C which included test scenario D), and then the list of actual test scenarios run in the "Scenario" column.  Test scenarios are the core unit of test execution, so each test scenario run is numbered in the order it was run.  The shorthand to refer to a particular scenario is "s" followed by the test scenario run index.  So, for instance, the first scenario run is "s1".  Clicking on the name of a test scenario will navigate to a page detailing the execution of that scenario, named s[N].html.

The columns following the "Scenario" column summarize which participants were active in each scenario by showing the outcomes of checks attributed to those participants in the test scenario.  For instance, a green checkmark under USS1 indicates that uss_qualifier verified USS1's compliance to at least one requirement and did not detect any non-compliance from USS1.

The final column indicates how long each test scenario took to run in minutes:seconds.

#### Skipped elements

When a test element is skipped, the cell that would have contained that element is populated with the name of the skipped element and the reason it was skipped in italics.  A skipped element does not necessarily indicate a problem.  The most common reason for a test element to be skipped is that a resource of a certain type is necessary to perform that element, but that resource was not provided in the test configuration.  This generally occurs when the test designer chooses not to include one or more available test features in their test configuration.  For instance, a jurisdiction with only one ASTM F3548-21 priority level would likely omit a resource containing flights at different priority levels, and therefore the test scenarios targeting requirements regarding differing priority levels would be skipped.

#### Execution errors

If the cell of a test scenario is colored red, that indicates an execution error occurred during that test scenario.  Execution errors always indicate a bug in uss_qualifier as all normal uss_qualifier operation should not raise uncaught exceptions.  Therefore, any execution errors should be reported to InterUSS unless the most recent version of uss_qualifier is not being used and the bug has already been fixed in a newer version of uss_qualifier.

## Scenario page

Each test scenario executed during the test run has its own page linked from the index page.  The heading names the test scenario and links to the documentation explaining what actions are conducted during test scenario execution.  This documentation [is programmatically linked](../../scenarios/README.md#documentation) to the actual execution of the test scenario.  Below the human-readable name of the scenario is the package-based identifier of the test scenario; the base `scenarios` package is the [scenarios folder](../../scenarios) of uss_qualifier.

### Resources

The "Resources" section helps identify the origin of each resource used in this particular execution of the test scenario.  The test scenario itself may call for, e.g., a control USS and a test USS.  This section identifies which resource was used for the control USS and which resource was used for the test USS.

### Events

The events table shows the reportable events that happened during this test scenario execution.  Test scenarios are segmented into test cases and test cases are segmented into test steps.  The content of the test case and test step columns name the test case and test step in which events occur, and provide links to the parts of the test scenario documentation defining those elements.  During a test step, the following events can occur:

* uss_qualifier makes a query (🌐 icon)
    * The top-level "[METHOD] [server] [response code]" summary of the query can be clicked to expand to see all recorded details of the query
* uss_qualifier performs a check (icon indicating outcome of check)
    * Icon and coloring indicate outcome of check
    * Main text is the name of the check (visible in documentation)
    * If check did not succeed, a summary of the problem is shown in italics with details below without italics
    * The participants associated with the check are identified in their corresponding columns to the right of the event description
* uss_qualifier makes a note (📓 icon)

Notes can also be made when not inside a test step.

Each event is identified by its index within the scenario execution.  The shorthand to refer to a particular event is "e" followed by the event index.  So, for instance, the first event in the test scenario run is "e1".  Because event indices are specific to a test scenario run, an event in a particular test run can be identified with the scenario index + event index; for instance, "s3e45".  Many unsuccessful checks reference the query or queries that are the basis for the failed check.

## Troubleshooting a failed check

To determine why a particular check failed for a particular participant, that participant should locate the first instance of that failed check.  This can be done by scrolling down the test scenario page until a red/yellow event for the participant is found.  The explanation of what the check is checking and the context around why that check corresponds to requirement compliance can be found in the documentation for the check which can be found by clicking the link on the test step name.  This test step documentation is found on the documentation page for the test scenario, and it may be necessary to read more of the earlier portions of the test scenario to understand what is happening in the check that failed.  When relevant, the failed check will link to a query event upon which the check's failure is based.  In this case, find the referenced query and review its content by clicking the event text to expand the query information.

If the reason for check failure cannot be determined via this means, a [test scenario bug Issue](https://github.com/interuss/monitoring/issues/new?template=bug_test_scenario.md) can be filed with InterUSS.  Be sure to attach at least the relevant test scenario sequence view page when possible, ideally the full zip of artifacts produced from the test run.
