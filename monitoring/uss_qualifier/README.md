# USS Qualifier: Automated Testing

## Introduction

The uss_qualifier tool in this folder performs
[automated testing](./automated_testing.md) to measure compliance to
requirements, including interoperability of multiple USS/USSPs.

## Usage

The `uss_qualifier` tool is a synchronous executable built into the `interuss/monitoring` Docker image.  To use the `interuss/monitoring` image to run uss_qualifier, specify a working directory of `/app/monitoring/uss_qualifier` and a command of `python main.py ${OPTIONS}` -- see [`run_locally.sh`](run_locally.sh) for an example that can be run on any local system that is running the required prerequisites (documented in message printed by run_locally.sh).

The primary input accepted by uss_qualifier is the "configuration" specified with the `--config` option.  This option should be a [reference to a configuration file](configurations/README.md) that the user has constructed or been provided to test the desired system for the desired characteristics.  If testing a standard local system (DSS + dummy auth + mock USSs), the user can specify an alternate configuration reference as a single argument to `run_locally.sh` (the default configuration is `configurations.dev.local_test`).

Several comma-separated "configurations" may be passed via the `--config` option.  If specified, the `--report` and `--config-output` options must have the same number of comma-separated values, which may be empty.

When building a custom configuration file, consider starting from [`configurations.dev.f3548_self_contained`](configurations/dev/f3548_self_contained.yaml), as it contains all information necessary to run the test without the usage of sometimes-configuring `$ref`s and `allOf`s.  See [configurations documentation](configurations/README.md) for more information.

### Quick start

This section provides a specific set of commands to execute uss_qualifier for demonstration purposes.

1. Check out this repository, making sure to initialize submodules: `git clone --recurse-submodules https://github.com/interuss/monitoring`
2. Go to repository root: `cd monitoring`
3. Bring up a local UTM ecosystem (DSS + dummy auth): `make start-locally`
4. Bring up mock USSs: `make start-uss-mocks`
5. Run uss_qualifier explicitly specifying a configuration to use: `monitoring/uss_qualifier/run_locally.sh configurations.dev.noop`

After building, uss_qualifier should take a few minutes to run and then `report_*.json` should appear in [monitoring/uss_qualifier](.)

At this point, uss_qualifier can be run again with a different configuration targeted at the development resources brought up in steps 3-4; for instance: `monitoring/uss_qualifier/run_locally.sh configurations.dev.self_contained_f3548`

Note that all baseline test configurations using local mocks can be run with `monitoring/uss_qualifier/run_locally.sh`.

### Artifacts

Part of a configuration defines artifacts that should be produced by the test run.  The raw output of the test run is a raw TestRunReport, which can be produced with the `raw_report` artifact option and has the file name `report.json`.  Given a `report.json`, any other artifacts can be generated with [`make_artifacts.sh`](./make_artifacts.sh).  From the repository root, for instance: `monitoring/uss_qualifier/make_artifacts.sh file://output/report.json configurations.personal.my_artifacts`.  That command loads the report at monitoring/uss_qualifier/output/report.json along with the configuration at monitoring/configurations/personal/my_artifacts.yaml and write the artifacts defined in the my_artifacts configuration.

To regenerate artifacts using just a raw TestRunReport (using the configuration embedded in the TestRunReport), only specify the report.  For example: `monitoring/uss_qualifier/make_artifacts.sh file://output/report.json`

### Local testing

See the [local testing page](local_testing.md) for more information regarding running uss_qualifier on a single local system.

## Troubleshooting

### Skipped actions

uss_qualifier is generally designed to skip test components when some prerequisites for those components are not met to enable testing of other parts of the systems under test until those prerequisites can be met.  Components are generally skipped when a necessary resource is not provided.  If you believe you have provided the resource that is claimed not to be provided, it is possible the resource could not be created due to another prerequisite not being met.  See console warnings at the beginning of test execution for more information, and/or set [`stop_when_resource_not_created`](./configurations/configuration.py) to `true` in your configuration's `execution` configuration to stop test execution when such a prerequisite is not met.

## Architecture

### Structure

* [Test scenarios](scenarios/README.md) are the core, mostly-self-contained, units of test runs.  Test scenarios are broken down into test cases, then test steps, then checks.
* [Test suites](suites/README.md) are static "playlists" of test scenarios (sometimes involving child test suites or action generators).
    * [Action generators](action_generators/README.md) are dynamic generators of test scenarios (sometimes via child test suites or action generators).
* [Test configurations](configurations/README.md) are inputs to uss_qualifier which define what testing is to be performed and how that testing is to be performed.
    * [Test resources](resources/README.md) provide information for where to find participants' systems and/or the ability to perform specific test behaviors.  They are specified in the test configuration and then used by test scenarios.

### Execution outline

When uss_qualifier is invoked, execution follows the general flow below:

#### Load test configuration

* Test configurations are dict-like files (JSON, YAML, Jsonnet) and may consist of multiple files for a single configuration.
* All referenced content is loaded and rendered into a concrete [USSQualifierConfiguration](configurations/configuration.py) instance.

#### Validate test configuration

Configuration is validated against configuration schema (unless skipped per command line flag).

* This only detects violations of the schema, not necessarily all errors in configuration.

#### Write rendered test configuration

Rendered configuration is written to file (if requested via command line flag).

* Configuration source files can be complex and non-trivial to understand; if this option is specified, the actual interpreted configuration will be output for inspection and verification by test designers or other interested parties.

#### Evaluate and log test definition

* The tests to perform are fully defined by the InterUSS `monitoring` codebase version (described by git commit hash + any local modifications) and test configuration.
* Test configuration is abbreviated with a test environment signature (hash of all elements of the test configuration labeled as "environment") and a test baseline signature (hash of all elements of the test configuration not labeled as "environment").
* The test definition description consists of the elements above and is logged (this information will also be included in the test report).

#### Exit early

uss_qualifier may exit early at this point without actually executing the test run (if requested via command line flag).

#### Execute test run

1. All resources specified in the test configuration are instantiated when possible.
    * Resources that cannot be instantiated are simply omitted from the resource pool unless the test configuration specifies that execution should stop when resources cannot be created.
    * All instantiated resources form the resource pool available to the top-level test action.
1. The top-level test action specified in the test configuration is instantiated.
    * Whenever a test suite is instantiated as an action, it instantiates all its child test actions, providing a subset of the resource pool to each child test action as specified in the test suite definition.
    * An action generator may instantiate its child test actions when the action generator is instantiated, or dynamically at runtime, or a combination of both.
        * Generally, test actions are instantiated as early as possible, so most action generators instantiate their child test actions when the action generator is instantiated.
    * Test scenario actions are instantiated by calling the constructor of the TestScenario class, expecting the non-optional resources in its constructor to be supplied in its resource pool.
1. The top-level test action is `run`.
    * All descendant test actions are run sequentially, depth-first (as a consequence of how test suites and action generators work).
    * Whenever a test action is about to be run, the execution criteria optionally provided in the test configuration are checked to see whether it should be skipped or not.
    * Any test action will be skipped when its required resources are not provided/available.
    * Each test action produces a test action report.  This report is incorporated hierarchically into the final test report.
1. The top-level test action's report (including a tree of reports from all descendant test actions that were run) is incorporated into a final [TestRunReport](reports/report.py).

#### Generate artifacts

Any artifacts specified in test configuration are generated.

* Artifacts are generated solely from the information in the final TestRunReport and the artifacts portion of the test configuration.
* `report.json` is the raw TestRunReport content (when generated as an artifact).
* Any other artifact [can be generated](#artifacts) after the test run is complete if `report.json` is provided.

#### Validate test report

Test report is evaluated in order to return the appropriate "success or error" execution code (if specified in test configuration).

### Verifiable capabilities

A test suite may define one or more verifiable "capabilities" and the criteria necessary to verify them for a participant.  These verifiable capabilities are intended to be used to indicate whether a participant has satisfied the requirements for an optional capability.

For instance, ASTM F3411-22a network remote identification includes the concept of an "intent-based network participant" who provides information about their overall flight intent, but not real-time telemetry.  A NetRID Service Provider is not required to support intent-based network participants, but if they do choose to support them, then they must follow a few requirements.  In this case, an "intent-based network participant support" capability may be defined to be verified only if uss_qualifier confirms compliance with the requirements regarding intent-based network participants.  If compliance to the intent-based network participants cannot be confirmed, the NetRID Service Provider under test may still be fully compliant with the standard; they just elected not to support this particular optional capability and would therefore be standard-compliant without verifying the "intent-based network participant support" capability.

As another example, ASTM F3411-22a does not require a NetRID Display Provider to provide Display Application clients with the serial number of an identified aircraft.  However, a particular jurisdiction may accept F3411-22a remote identification as a means of compliance only if Display Applications are capable of providing the viewer with the aircraft serial number.  In this case, the ASTM F3411-22a test suite could define a "serial number" capability indicating that a Display Provider provides the correct aircraft serial number to its Display Application clients, and then the test suite for the jurisdiction may define a "qualified in jurisdiction" capability which is not verified unless the ASTM F3411-22a test suite's "serial number" capability is verified (among other criteria).
