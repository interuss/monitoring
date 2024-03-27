# ASTM SCD DSS: Operational Intent Reference Synchronization test scenario

## Overview

Verifies that all CRUD operations on operational intent references performed on a given DSS instance
are properly propagated to every other DSS instance participating in the deployment.

## Resources

### dss

[`DSSInstanceResource`](../../../../../resources/astm/f3548/v21/dss.py) the DSS instance through which entities are created, modified and deleted.

### other_instances

[`DSSInstancesResource`](../../../../../resources/astm/f3548/v21/dss.py) pointing to the DSS instances used to confirm that entities are properly propagated.

### id_generator

[`IDGeneratorResource`](../../../../../resources/interuss/id_generator.py) providing the operational intent reference ID for this scenario.

### planning_area

[`PlanningAreaResource`](../../../../../resources/astm/f3548/v21/planning_area.py) describes the 3D volume in which operational intent reference will be created.

### client_identity

[`ClientIdentityResource`](../../../../../resources/communications/client_identity.py) to be used for this scenario.

## Setup test case

### [Ensure clean workspace test step](../clean_workspace.md)

This step ensures that no operational intent reference with the known test ID exists in the DSS.

## OIR synchronization test case

This test case creates an operational intent reference on the main DSS, and verifies that it is properly synchronized to the other DSS instances.

It then goes on to mutate and delete it, each time confirming that all other DSSes return the expected results.

### Create OIR validation test step

#### [Create OIR](../fragments/oir/crud/create_correct.md)

Verify that an operational intent reference can be created on the primary DSS.

#### [OIR Content is correct](../fragments/oir/validate/correctness.md)

Verify that the operational intent reference returned by the DSS under test is properly formatted and contains the expected content.

### Query newly created OIR test step

Query the created operational intent at every DSS provided in `dss_instances`.

#### [Get OIR](../fragments/oir/crud/read.md)

Confirms that each DSS provides access to the created operational intent reference,

#### [OIR is synchronized](../fragments/oir/sync.md)

Confirm that the operational intent reference that was just created is properly synchronized across all DSS instances.

#### [OIR Content is correct](../fragments/oir/validate/correctness.md)

Verify that the operational intent reference returned by every DSS is correctly formatted and corresponds to what was created earlier.

#### [OIR Versions are correct](../fragments/oir/validate/non_mutated.md)

Verify that the operational intent reference's version fields are as expected.

### Mutate OIR test step

This test step mutates the previously created operational intent reference to verify that the DSS reacts properly: notably, it checks that the operational intent reference version is updated,
including for changes that are not directly visible, such as changing the operational intent reference's footprint.

#### [Update OIR](../fragments/oir/crud/update_correct.md)

Confirm that the operational intent reference can be mutated.

#### [Validate OIR](../fragments/oir/validate/correctness.md)

Verify that the operational intent reference returned by the DSS is properly formatted and contains the correct content.

#### [OIR Versions are correct](../fragments/oir/validate/mutated.md)

Verify that the operational intent reference's version fields have been updated.

### Query updated OIR test step

Query the updated operational intent reference at every DSS provided in `dss_instances`.

#### [OIR is synchronized](../fragments/oir/sync.md)

Confirm that the operational intent reference that was just mutated is properly synchronized across all DSS instances.

#### [Get OIR](../fragments/oir/crud/read.md)

Confirms that the operational intent reference that was just mutated can be retrieved from any DSS.

#### [Validate OIR](../fragments/oir/validate/correctness.md)

Verify that the operational intent reference returned by every DSS is correctly formatted and corresponds to what was mutated earlier.

#### [OIR Versions are correct](../fragments/oir/validate/non_mutated.md)

Verify that the operational intent reference's version fields are as expected.

## [Cleanup](../clean_workspace.md)
