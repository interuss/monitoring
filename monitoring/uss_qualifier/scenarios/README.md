# Test scenarios

## Definition

A test scenario is a logical, self-contained scenario designed to test specific sets of functionality of the systems under test.  The activities in a test scenario should read like a narrative of a simple play with a single plot.

## Structure

A test scenario is separated into of a list of test cases, each of which are separated into a list of test steps, each of which have a set of checks that may be performed.  A test scenario is implemented as [`TestScenario`](scenario.py) subclass, and the context of current test case and test step is controlled by a state machine build into `TestScenario`, as is the performance of checks.

### Test cases

1. A test case is a single holistic operation or action performed as part of a larger test scenario.
    * Test cases are like acts in the "play" of the test scenario they are a part of.
    * Test cases are typically the "gray headers” of the overview sequence diagrams.
2. A given test case belongs to exactly one test scenario.
3. A test case is composed of a list of test steps.
    * Each test step on the list is executed sequentially.

### Test steps

1. A test step is a single task that must be performed in order to accomplish its associated test case.
    * Test steps are like scenes in the "play/act" of the test scenario/test case they are a part of.
2. A given test step belongs to exactly one test case.
3. A test step should generally have a list of checks associated with it.

### Checks

1. A check is the lowest-level thing automated testing does – it is a single pass/fail evaluation of a single criterion for a requirement.
2. A check evaluates information collected during the actions performed for a test step.
3. A given check belongs to exactly one test step.
4. Each check defines which requirement(s) are not met if the check fails.
5. In nearly all cases, the test participant(s) to which a check pertains should be specified when performing the check.
    * If the test participant is not specified, then either everyone involved in a test or no one is responsible for meeting the requirements of that check, and this is very rarely appropriate.

## Creation

Test scenarios will usually be enumerated/identified/created by mapping a list of requirements onto a set of test scenarios (e.g., [NetRID](https://docs.google.com/spreadsheets/d/1YByckmK6hfMrGec53CxRM2BPvcgm6HQNoFxOrOEfrUQ/edit#gid=0), [Flight Authorisation](https://docs.google.com/spreadsheets/d/1IJkNS21Ps-2411LGhXBqWF7inQnPVeEA23dWjXpCR-M/edit#gid=0), [ED-269](https://docs.google.com/spreadsheets/d/1NIlRHtWzBXOyJ58pYimhDQDqsEyToTQRu2ma3AYXWEU/edit)).  To form a complete set of scenarios to cover a set of requirements:

    While unmapped requirements still exist:
        Create new, simple test scenario that verifies a set of remaining unmapped requirements.

See [CONTRIBUTING.md](../../../CONTRIBUTING.md#ussqualifier-test-scenarios) for more information on how to develop test scenarios.

## Resources

Most test scenarios will require [test resources](../resources/README.md) (like NetRID telemetry to inject, NetRID service providers under test, etc) usually customized to the ecosystem in which the tests are being performed.  A test scenario declares what kind of resource(s) it requires, and a test suite identifies which available resources should be used to fulfill each test scenario's needs.

## Documentation

Traceability between requirements and test activities is of the utmost importance in automated testing.  As such, every test scenario must be documented, and that documentation must follow a precise format.  Conformance to this format is [checked by an automated test](../scripts/validate_test_definitions.sh) before changes to test scenarios or their documentation can be submitted to this repository.

Documentation requirements include:

### Documentation location

The documentation must be located in a .md file with the same name as the Python file that defines the `TestScenario`.  For instance, if a `NominalBehavior` class inherited from `TestScenario` and was defined in nominal_behavior.py, then documentation for `NominalBehavior` would be expected in nominal_behavior.md located in the same folder as nominal_behavior.py.

### Scenario name

The first line of the documentation file must be a top-level section header with the name of the test scenario ending in " test scenario".  Example: `# ASTM NetRID nominal behavior test scenario`

### Resources

A main section in the documentation must be named "Resources" (example: `## Resources`).  This section must have a subsection for each resource required by the test scenario, and each of these sections must be named according to the parameter in the `TestScenario` subclass's constructor for that resource.  For example, if a test scenario were defined as:

```python
class NominalBehavior(TestScenario):
    def __init__(self, flights_data: FlightDataResource,
                 service_providers: NetRIDServiceProviders:
        ...
```

...then the Resources section (`# Resources`) of the documentation would be expected to have two subsections: one for `flights_data` (`## flights_data`) and one for `service_providers` (`## service_providers`).  These sections should generally explain the purpose, use, expectations, and/or requirements for the resources.

### Test cases

A scenario must document at least one test case (otherwise the scenario is doing nothing).  Each test case must be documented via a main section in the documentation named with a " test case" suffix (example: `## Nominal flight test case`).

### Test steps

Each test case in the documentation must document at least one test step (otherwise nothing is happening in the test case).  Each test step must be documented via a subsection of the parent test case named with a " test step" suffix (example: `### Injection test step`).

If the entire test step heading is enclosed in a link, the contents of that linked file will be used to pre-populate the test step (example: `### [Plan flight test step](plan_flight_fragment.md)`) before reading the content in this section.  The linked file must follow the format requirements for a test step, but with the first line being a top-level heading ending with " test step fragment" (example: `# Plan flight test step fragment`).

Multiple test step fragments may be included in a test step by linking to the test step fragment in a heading one level lower than the test step itself, and these lower-level headings may be combined with [checks](#test-checks) specific to the test step; for instance:

```markdown
### Plan flight test step

This step does (a particular thing).

#### [Actually plan flight](plan_flight_fragment.md)

#### Special check

If the system under test doesn't Foo, then requirement **Bar** will not be met.

#### [Ensure flight baz](check_flight_baz_fragment.md)
```

### Test checks

Each check a test step performs that may result in a finding/issue must be documented via a subsection of the parent test step, named with a " check" suffix, and a prefix according to the severity of failure of that check (example: `#### 🛑 Successful injection check`).

The severity of a failure of the check should be indicated with one of the following unicode symbols (these can be copied and pasted into the Markdown documentation):

* ℹ️ Low severity: No requirement was violated, but this finding may be useful for improvement.
* ⚠️ Medium severity: A requirement was violated, but the test scenario can continue.
* 🛑 High severity: The test scenario should terminate after cleaning up.
* ☢ Critical severity: Not only can the test scenario not continue, the entire test run should stop.

A check should document the requirement(s) violated if the check fails.  Requirements are identified by putting a strong emphasis/bold style around the requirement ID (example: `**astm.f3411.v19.NET0420**`).  The description of a check should generally explain why the relevant requirement would fail when that information is useful, but the requirement itself should generally not be re-iterated in this description.  If the check is self-evident from the requirement, the requirement can be noted without further explanation.

Any requirements identified (e.g., `**astm.f3411.v19.NET0420**`) must be documented as well.  See [the requirements documentation](../requirements/README.md) for more information.

If the text of this section includes `TODO:`, then the check will be indicated as in development rather than complete.  Documentation of intended checks with, e.g., `TODO: Implement` prior to the start of Python development is highly encouraged.

### Cleanup phase

If a test scenario wants to perform a cleanup procedure following any non-error termination of the rest of the scenario, it must:

1) Override the `cleanup()` method on the base `TestScenario` class
2) Include a main section in the documentation named "Cleanup" that is documented like a test step (including, e.g., test checks when appropriate).

The `cleanup()` method may not be overridden unless the cleanup phase is documented for that test scenario.  If the cleanup phase is documented for the test scenario, the `cleanup()` method must be overridden.

### Reserved stylings

#### Strong emphasis

The strong emphasis styling (`**example**`) may only be used to identify requirement IDs (see "Test checks" section).  Requirement IDs must also link to the document in which they are defined, but this can be performed automatically with `make format` (which transforms, e.g., `**example.req.ID**` into `**[example.req.ID](path/to/example/req.md)`).
