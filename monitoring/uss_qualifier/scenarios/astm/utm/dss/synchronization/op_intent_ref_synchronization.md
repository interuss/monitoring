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

### Retrieve newly created OIR test step

Retrieve and validate synchronization of the created operational intent at every DSS provided in `dss_instances`.

#### [Get OIR query](../fragments/oir/crud/read_query.md)

Check that read query succeeds.

#### Newly created OIR can be consistently retrieved from all DSS instances check

If the operational intent retrieved from a secondary DSS instance is not consistent with the newly created one on the
primary DSS instance, this check will fail per **[astm.f3548.v21.DSS0210,A2-7-2,1a](../../../../../requirements/astm/f3548/v21.md)**, **[astm.f3548.v21.DSS0210,A2-7-2,1d](../../../../../requirements/astm/f3548/v21.md)**,
, **[astm.f3548.v21.DSS0215](../../../../../requirements/astm/f3548/v21.md)** and **[astm.f3548.v21.DSS0020](../../../../../requirements/astm/f3548/v21.md)**.

#### [OIR is synchronized](../fragments/oir/sync.md)

Confirm that each DSS provides direct access to the created operational intent reference.
Confirm that the operational intent reference that was just created is properly synchronized across all DSS instances.

### Search for newly created OIR test step

Search for and validate synchronization of the created operational intent at every DSS provided in `dss_instances`.

#### [Search OIR](../fragments/oir/crud/search_query.md)

Check that search query succeeds.

#### Newly created OIR can be consistently searched for from all DSS instances check

If the operational intent searched from a secondary DSS instance is not consistent with the newly created one on the
primary DSS instance, this check will fail per **[astm.f3548.v21.DSS0210,A2-7-2,1a](../../../../../requirements/astm/f3548/v21.md)**, **[astm.f3548.v21.DSS0210,A2-7-2,1c](../../../../../requirements/astm/f3548/v21.md)**,
, **[astm.f3548.v21.DSS0215](../../../../../requirements/astm/f3548/v21.md)** and **[astm.f3548.v21.DSS0020](../../../../../requirements/astm/f3548/v21.md)**.

#### [OIR is synchronized](../fragments/oir/sync.md)

Confirm that each DSS returns the operational intent in relevant search results.
Confirm that the operational intent reference that was just created is properly synchronized across all DSS instances.

### Mutate OIR test step

This test step mutates the previously created operational intent reference to verify that the DSS reacts properly: notably, it checks that the operational intent reference version is updated,
including for changes that are not directly visible, such as changing the operational intent reference's footprint.

#### [Update OIR](../fragments/oir/crud/update_correct.md)

Confirm that the operational intent reference can be mutated.

#### [Validate OIR](../fragments/oir/validate/correctness.md)

Verify that the operational intent reference returned by the DSS is properly formatted and contains the correct content.

#### [OIR Versions are correct](../fragments/oir/validate/mutated.md)

Verify that the operational intent reference's version fields have been updated.

### Retrieve updated OIR test step

Retrieve and validate synchronization of the updated operational intent at every DSS provided in `dss_instances`.

#### [Get OIR query](../fragments/oir/crud/read_query.md)

Check that read query succeeds.

#### Updated OIR can be consistently retrieved from all DSS instances check

If the operational intent retrieved from a secondary DSS instance is not consistent with the updated one on the
primary DSS instance, this check will fail per **[astm.f3548.v21.DSS0210,A2-7-2,1b](../../../../../requirements/astm/f3548/v21.md)**
and **[astm.f3548.v21.DSS0210,A2-7-2,1d](../../../../../requirements/astm/f3548/v21.md)**.

#### [OIR is synchronized](../fragments/oir/sync.md)

Confirm that each DSS provides direct access to the updated operational intent reference.
Confirm that the operational intent reference that was just updated is properly synchronized across all DSS instances.

### Search for updated OIR test step

Search for and validate synchronization of the updated operational intent at every DSS provided in `dss_instances`.

#### [Search OIR](../fragments/oir/crud/search_query.md)

Check that search query succeeds.

#### Updated OIR can be consistently searched for from all DSS instances check

If the operational intent searched from a secondary DSS instance is not consistent with the updated one on the
primary DSS instance, this check will fail per **[astm.f3548.v21.DSS0210,A2-7-2,1b](../../../../../requirements/astm/f3548/v21.md)**
and **[astm.f3548.v21.DSS0210,A2-7-2,1c](../../../../../requirements/astm/f3548/v21.md)**.

#### [OIR is synchronized](../fragments/oir/sync.md)

Confirm that each DSS returns the operational intent in relevant search results.
Confirm that the operational intent reference that was just updated is properly synchronized across all DSS instances.

### Delete OIR test step

Attempt to delete the operational intent reference in various ways and ensure that the DSS reacts properly.

This also checks that the operational intent reference data returned by a successful deletion is correct.

#### [Delete OIR](../fragments/oir/crud/delete.md)

Confirm that an operational intent reference can be deleted.

#### [Validate OIR](../fragments/oir/validate/correctness.md)

Verify that the operational intent reference returned by the DSS via the deletion is properly formatted and contains the correct content.

#### [OIR Versions are correct](../fragments/oir/validate/non_mutated.md)

Verify that the operational intent reference's version fields are as expected.

### Query deleted OIR test step

Attempt to query and search for the deleted operational intent reference in various ways

#### [Get OIR query](../fragments/oir/crud/read_query.md)

Check that read query succeeds.

#### 🛑 Deleted OIR cannot be retrieved from all DSS instances check

If a DSS returns an operational intent reference that was previously successfully deleted from the primary DSS,
either one of the primary DSS or the DSS that returned the operational intent reference is in violation of **[astm.f3548.v21.DSS0210,2a](../../../../../requirements/astm/f3548/v21.md)**
and **[astm.f3548.v21.DSS0210,A2-7-2,3b](../../../../../requirements/astm/f3548/v21.md)**.

#### [Search OIR](../fragments/oir/crud/search_query.md)

Check that search query succeeds.

#### 🛑 Deleted OIR cannot be searched for from all DSS instances check

If a DSS returns an operational intent reference that was previously successfully deleted from the primary DSS,
either one of the primary DSS or the DSS that returned the operational intent reference is in violation of **[astm.f3548.v21.DSS0210,2a](../../../../../requirements/astm/f3548/v21.md)**
and **[astm.f3548.v21.DSS0210,A2-7-2,3a](../../../../../requirements/astm/f3548/v21.md)**.

## [Cleanup](../clean_workspace.md)
