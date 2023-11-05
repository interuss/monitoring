# USS Qualifier: Automated Testing

## Introduction

The uss_qualifier tool in this folder automates verifying compliance to requirements and interoperability of multiple USS/USSPs.

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

Part of a configuration defines artifacts that should be produced by the test run.  The raw output of the test run is a raw TestRunReport, which can be produced with the `raw_report` artifact option and has the file name `report.json`.  Given a `report.json`, any other artifacts can be generated with [`make_artifacts.sh`](./make_artifacts.sh).  From the repository root, for instance: `monitoring/uss_qualifier/make_artifacts.sh configurations.personal.my_artifacts file://output/report.json`.  That command loads the report at monitoring/uss_qualifier/output/report.json along with the configuration at monitoring/configurations/personal/my_artifacts.yaml and write the artifacts defined in the my_artifacts configuration.

### Local testing

See the [local testing page](local_testing.md) for more information regarding running uss_qualifier on a single local system.

## Architecture

* [Test suites](suites/README.md)
* [Test scenarios](scenarios/README.md) (includes test case, test step, check breakdown)
* [Test configurations](configurations/README.md)
* [Test resources](resources/README.md)

### Verifiable capabilities

A test suite may define one or more verifiable "capabilities" and the criteria necessary to verify them for a participant.  These verifiable capabilities are intended to be used to indicate whether a participant has satisfied the requirements for an optional capability.

For instance, ASTM F3411-22a network remote identification includes the concept of an "intent-based network participant" who provides information about their overall flight intent, but not real-time telemetry.  A NetRID Service Provider is not required to support intent-based network participants, but if they do choose to support them, then they must follow a few requirements.  In this case, an "intent-based network participant support" capability may be defined to be verified only if uss_qualifier confirms compliance with the requirements regarding intent-based network participants.  If compliance to the intent-based network participants cannot be confirmed, the NetRID Service Provider under test may still be fully compliant with the standard; they just elected not to support this particular optional capability and would therefore be standard-compliant without verifying the "intent-based network participant support" capability.

As another example, ASTM F3411-22a does not require a NetRID Display Provider to provide Display Application clients with the serial number of an identified aircraft.  However, a particular jurisdiction may accept F3411-22a remote identification as a means of compliance only if Display Applications are capable of providing the viewer with the aircraft serial number.  In this case, the ASTM F3411-22a test suite could define a "serial number" capability indicating that a Display Provider provides the correct aircraft serial number to its Display Application clients, and then the test suite for the jurisdiction may define a "qualified in jurisdiction" capability which is not verified unless the ASTM F3411-22a test suite's "serial number" capability is verified (among other criteria).
