# ASTM SCD DSS: Constraint Reference Synchronization test scenario

## Overview

Verifies that all CRUD operations on constraint references performed on a given DSS instance
are properly propagated to every other DSS instance participating in the deployment.

## Resources

### dss

[`DSSInstanceResource`](../../../../../resources/astm/f3548/v21/dss.py) the DSS instance through which entities are created, modified and deleted.

### other_instances

[`DSSInstancesResource`](../../../../../resources/astm/f3548/v21/dss.py) pointing to the DSS instances used to confirm that entities are properly propagated.

### id_generator

[`IDGeneratorResource`](../../../../../resources/interuss/id_generator.py) providing the constraint reference ID for this scenario.

### planning_area

[`PlanningAreaResource`](../../../../../resources/planning_area.py) describes the 3D volume in which constraint reference will be created.

### client_identity

[`ClientIdentityResource`](../../../../../resources/communications/client_identity.py) to be used for this scenario.

## Setup test case

### Ensure clean workspace test step

#### [Clean any existing constraint references with known test IDs](../clean_workspace_constraints.md)

## CR synchronization test case

This test case creates an constraint reference on the main DSS, and verifies that it is properly synchronized to the other DSS instances.

It then goes on to mutate and delete it, each time confirming that all other DSSes return the expected results.

### Create CR validation test step

#### [Create CR](../fragments/cr/crud/create_correct.md)

Verify that an constraint reference can be created on the primary DSS.

#### [CR Content is correct](../fragments/cr/validate/correctness.md)

Verify that the constraint reference returned by the DSS under test is properly formatted and contains the expected content.

### Retrieve newly created CR test step

Retrieve and validate synchronization of the created constraint at every DSS provided in `dss_instances`.

#### [Get CR query](../fragments/cr/crud/read_correct.md)

Check that read query succeeds.

#### 🛑 Newly created CR can be consistently retrieved from all DSS instances check

If the constraint retrieved from a secondary DSS instance is not consistent with the newly created one on the
primary DSS instance, this check will fail per **[astm.f3548.v21.DSS0210,A2-7-2,1a](../../../../../requirements/astm/f3548/v21.md)**, **[astm.f3548.v21.DSS0210,A2-7-2,1f](../../../../../requirements/astm/f3548/v21.md)**,
**[astm.f3548.v21.DSS0215](../../../../../requirements/astm/f3548/v21.md)** and **[astm.f3548.v21.DSS0020](../../../../../requirements/astm/f3548/v21.md)**.

#### [CR is synchronized](../fragments/cr/sync.md)

Confirm that each DSS provides direct access to the created constraint reference.
Confirm that the constraint reference that was just created is properly synchronized across all DSS instances.

#### [CR Content is correct](../fragments/cr/validate/correctness.md)

Sanity check on the rest of the content and format of the response.

#### [CR version is correct](../fragments/cr/validate/non_mutated.md)

Confirm that version and OIR are as expected.

### Search for newly created CR test step

Search for and validate synchronization of the created constraint at every DSS provided in `dss_instances`.

#### [Search CR](../fragments/cr/crud/search_correct.md)

Check that search query succeeds and the response is well-formed.

#### 🛑 Newly created CR can be consistently searched for from all DSS instances check

If the constraint searched from a secondary DSS instance is not consistent with the newly created one on the
primary DSS instance, this check will fail per **[astm.f3548.v21.DSS0210,A2-7-2,1a](../../../../../requirements/astm/f3548/v21.md)**, **[astm.f3548.v21.DSS0210,A2-7-2,1e](../../../../../requirements/astm/f3548/v21.md)**,
, **[astm.f3548.v21.DSS0215](../../../../../requirements/astm/f3548/v21.md)** and **[astm.f3548.v21.DSS0020](../../../../../requirements/astm/f3548/v21.md)**.

#### [CR is synchronized](../fragments/cr/sync.md)

Confirm that each DSS returns the constraint in relevant search results.
Confirm that the constraint reference that was just created is properly synchronized across all DSS instances.

#### [CR content is correct](../fragments/cr/validate/correctness.md)

#### [CR version is correct](../fragments/cr/validate/non_mutated.md)

### Mutate CR test step

This test step mutates the previously created constraint reference to verify that the DSS reacts properly: notably, it checks that the constraint reference version is updated,
including for changes that are not directly visible, such as changing the constraint reference's footprint.

#### [Update CR](../fragments/cr/crud/update_correct.md)

Confirm that the constraint reference can be mutated.

#### [Validate CR](../fragments/cr/validate/correctness.md)

Verify that the constraint reference returned by the DSS is properly formatted and contains the correct content.

#### [CR Versions are correct](../fragments/cr/validate/mutated.md)

Verify that the constraint reference's version fields have been updated.

### Retrieve updated CR test step

Retrieve and validate synchronization of the updated constraint at every DSS provided in `dss_instances`.

#### [Get CR query](../fragments/cr/crud/read_correct.md)

Check that read query succeeds and the response is well-formed.

#### 🛑 Updated CR can be consistently retrieved from all DSS instances check

If the constraint retrieved from a secondary DSS instance is not consistent with the updated one on the
primary DSS instance, this check will fail per **[astm.f3548.v21.DSS0210,A2-7-2,1b](../../../../../requirements/astm/f3548/v21.md)**, **[astm.f3548.v21.DSS0210,A2-7-2,1d](../../../../../requirements/astm/f3548/v21.md)**,
**[astm.f3548.v21.DSS0215](../../../../../requirements/astm/f3548/v21.md)** and **[astm.f3548.v21.DSS0020](../../../../../requirements/astm/f3548/v21.md)**.

#### [CR is synchronized](../fragments/cr/sync.md)

Confirm that each DSS provides direct access to the updated constraint reference.
Confirm that the constraint reference that was just updated is properly synchronized across all DSS instances.

#### [CR Content is correct](../fragments/cr/validate/correctness.md)

#### [CR version is correct](../fragments/cr/validate/non_mutated.md)

### Search for updated CR test step

Search for and validate synchronization of the updated constraint at every DSS provided in `dss_instances`.

#### [Search CR](../fragments/cr/crud/search_correct.md)

Check that search query succeeds and the response is well-formed.

#### 🛑 Updated CR can be consistently searched for from all DSS instances check

If the constraint searched from a secondary DSS instance is not consistent with the updated one on the
primary DSS instance, this check will fail per **[astm.f3548.v21.DSS0210,A2-7-2,1b](../../../../../requirements/astm/f3548/v21.md)**, **[astm.f3548.v21.DSS0210,A2-7-2,1e](../../../../../requirements/astm/f3548/v21.md)**,
**[astm.f3548.v21.DSS0215](../../../../../requirements/astm/f3548/v21.md)** and **[astm.f3548.v21.DSS0020](../../../../../requirements/astm/f3548/v21.md)**.

#### [CR is synchronized](../fragments/cr/sync.md)

Confirm that each DSS returns the constraint in relevant search results.
Confirm that the constraint reference that was just updated is properly synchronized across all DSS instances.

#### [CR content is correct](../fragments/cr/validate/correctness.md)

#### [CR version is correct](../fragments/cr/validate/non_mutated.md)

### Delete CR test step

Attempt to delete the constraint reference in various ways and ensure that the DSS reacts properly.

This also checks that the constraint reference data returned by a successful deletion is correct.

#### [Delete CR](../fragments/cr/crud/delete.md)

Confirm that an constraint reference can be deleted.

#### [Validate CR](../fragments/cr/validate/correctness.md)

Verify that the constraint reference returned by the DSS via the deletion is properly formatted and contains the correct content.

#### [CR Versions are correct](../fragments/cr/validate/non_mutated.md)

Verify that the constraint reference's version fields are as expected.

### Query deleted CR test step

Attempt to query and search for the deleted constraint reference in various ways

#### [Get CR query](../fragments/cr/crud/read_correct.md)

Check that read query succeeds.

#### 🛑 Deleted CR cannot be retrieved from all DSS instances check

If a DSS returns an constraint reference that was previously successfully deleted from the primary DSS,
either one of the primary DSS or the DSS that returned the constraint reference is in violation of **[astm.f3548.v21.DSS0210,2a](../../../../../requirements/astm/f3548/v21.md)**, **[astm.f3548.v21.DSS0210,A2-7-2,3b](../../../../../requirements/astm/f3548/v21.md)**,
**[astm.f3548.v21.DSS0215](../../../../../requirements/astm/f3548/v21.md)** and **[astm.f3548.v21.DSS0020](../../../../../requirements/astm/f3548/v21.md)**.

#### [Search CR](../fragments/cr/crud/search_query.md)

Check that search query succeeds.

#### 🛑 Deleted CR cannot be searched for from all DSS instances check

If a DSS returns an constraint reference that was previously successfully deleted from the primary DSS,
either one of the primary DSS or the DSS that returned the constraint reference is in violation of **[astm.f3548.v21.DSS0210,2a](../../../../../requirements/astm/f3548/v21.md)**, **[astm.f3548.v21.DSS0210,A2-7-2,3a](../../../../../requirements/astm/f3548/v21.md)**,
**[astm.f3548.v21.DSS0215](../../../../../requirements/astm/f3548/v21.md)** and **[astm.f3548.v21.DSS0020](../../../../../requirements/astm/f3548/v21.md)**.

## [Cleanup](../clean_workspace_constraints.md)
