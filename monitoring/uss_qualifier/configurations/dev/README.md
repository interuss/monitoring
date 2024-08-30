# Development test configurations

The [test configurations](../README.md) in this folder represent common/useful test situations.

## [dss_probing](dss_probing.yaml)

Runs all tests available for an InterUSS DSS implementation deployment.

## [f3548_self_contained](f3548_self_contained.yaml)

A self-contained (all content is contained in a single YAML configuration file) test configuration which happens to test compliance to ASTM F3548-21 requirements in a particular regulatory environment.

This configuration is a good example to start from to understand

## [general_flight_auth](general_flight_auth.jsonnet)

Demonstration of a test where a list of flight planning attempts has a corresponding list of expected outcomes.

Demonstrates the use of jsonnet as a file format.

## [generate_rid_test_data](generate_rid_test_data.yaml)

Demonstrates simple in-configuration test suite definition with short test actions that don't have external dependencies.

## [geoawareness_cis](geoawareness_cis.yaml)

Demonstration of a test where a list of expected geospatial map feature queries has the corresponding expected outcomes.

## [message_signing](message_signing.yaml)

Exercise of automated tests for message signing (not well-developed yet).


## [netrid_v19](netrid_v19.yaml)

Verification of ASTM F3411-19 network remote identification requirements.

## [netrid_v22a](netrid_v22a.yaml)

Verification of ASTM F3411-22a network remote identification requirements.

## [noop](noop.yaml)

Simple configuration performing nearly no action to verify that uss_qualifier runs correctly.

## [uspace](uspace.yaml)

Verifies requirements for U-space Service Providers using ASTM standards (F3411-22a + F3548-21) as means of compliance.

## [uspace_f3548](uspace_f3548.yaml)

Same configuration as [uspace](#uspace), except only the portions related to ASTM F3548-21 verification are executed (other parts are skipped).

## [utm_implementation_us](utm_implementation_us.jsonnet)

Intended to be an InterUSS interpretation of how to verify the requirements of the [US Shared Airspace group](https://github.com/utmimplementationus/getstarted) verified via automated testing as documented in their [Requirements Traceability Matrix for Strategic Coordination](https://github.com/utmimplementationus/getstarted/blob/main/docs/Strategic_Coordination_Compliance_Matrix_v1.0.xlsx).  Note that this is merely InterUSS's interpretation of the publicly-available information for that project and this test configuration may not exactly match the test configuration actually in use by that group (which is not organizationally affiliated with InterUSS).  InterUSS welcomes contributions to change this test configuration to better align with the intent of that group.

The baseline portion of the test configuration is found in [baseline.libsonnet](utm_implementation_us_lib/baseline.libsonnet) and the environmental portion of the test configuration is found in [env_all.libsonnet](utm_implementation_us_lib/local/env_all.libsonnet).  The top-level test configuration [utm_implementation_us.jsonnet](utm_implementation_us.jsonnet) combines the test baseline with the test environment to form a full test configuration.

### Environment characteristics

Some characteristics of this pseudo-regulatory environment are:

1. ASTM F3548-21 is being used
2. Participants perform Strategic Coordination only
3. Only one priority level is defined (level 0) and conflicts are not permitted at that priority level
4. No participant is authorized to perform Conformance Monitoring for Situational Awareness
5. No participant is authorized to act as availability arbitrator outside DSS functionality verification
6. No constraints are used (management nor processing)

### Adapting test configuration to a different test environment

To adapt this configuration to target a non-local ecosystem and USS:
* Make appropriately-named copies of the environmental and top-level configurations.
    * For instance, if testing in a pre-qualification environment, appropriate renaming might be:
        * utm_implementation_us.jsonnet -> utm_implementation_us_prequal.jsonnet
        * local (folder) -> prequal (folder)
    * These appropriately-named copies may be put into the [personal](../personal) folder to make modifications without affecting git-tracked files.
* Edit the new top-level configuration (e.g., utm_implementation_us_prequal.jsonnet) to point to the appropriate test baseline and test environment
    * The relative path of baseline.libsonnet may need to be adjusted.  For instance, if the top-level configuration is now in the personal folder, `import 'utm_implementation_us_lib/baseline.libsonnet'` must be changed to `import '../dev/utm_implementation_us_lib/baseline.libsonnet'`
    * The imported filename for the environment must be updated to the new environment filename (e.g., prequal/env_all.jsonnet)
* Edit the new participant-agnostic environmental configuration (e.g., prequal/env.libsonnet) to accurately describe the environment in which the new test is being conducted.
    * When referring to information specified by participant, create and use a new environment identifier -- i.e., change participant.local_env.* to, e.g., participant.prequal_env.*
* Edit and rename environmental configurations for participants (e.g., uss1.libsonnet, uss2.libsonnet) to accurately describe these participants and their systems under test in the new environment.
    * A new field/block should be added to the top-level participant config to capture the new environment information (e.g., prequal_env), matching the name chosen in the previous step
    * The content of this field/block can be copied from existing environment information (e.g., the local_env field/block)
* Edit the new participant-specific environmental configuration (e.g., prequal/env_all.libsonnet) to accurately describe the participants in the new environment.
