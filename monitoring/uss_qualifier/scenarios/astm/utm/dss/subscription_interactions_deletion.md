# ASTM SCD DSS: Subscription and entity deletion interaction test scenario

## Overview

Create and mutate subscriptions as well as entities, and verify that the DSS handles notifications and expiry correctly.

## Resources

### dss

[`DSSInstanceResource`](../../../../resources/astm/f3548/v21/dss.py) to be tested in this scenario.

### other_instances

[`DSSInstancesResource`](../../../../resources/astm/f3548/v21/dss.py) pointing to the DSS instances used to confirm that entities are properly propagated.

### id_generator

[`IDGeneratorResource`](../../../../resources/interuss/id_generator.py) providing the Subscription IDs for this scenario.

### planning_area

[`PlanningAreaResource`](../../../../resources/planning_area.py) describes the 3D volume in which subscriptions will be created.

### utm_client_identity

[`ClientIdentityResource`](../../../../resources/communications/client_identity.py) provides the identity that will be used to interact with the DSS.

### shared_asset_coordinator

Optional SharedAssetCoordinatorResource that coordinates exclusive access to USS availability states in the DSS pool.
Creating and modifying operational intents requires the test USS to remain available, so this scenario acquires ownership before setup and holds it through cleanup.
Ownership is automatically released by the scenario's ExitStack. When no coordinator is provided, no shared-asset coordination is performed.

## Setup test case

### Acquire exclusive DSS availability access test step

This step is performed only when a shared asset coordinator is provided.
Acquire exclusive access to USS availability states so another scenario cannot mark the test USS Down while this scenario creates or modifies operational intents.

#### 🛑 DSS availability access acquired check

If the shared asset coordinator does not grant exclusive access to USS availability states in the DSS pool, the coordinator and/or test design will have failed to meet **[interuss.automated_testing.coordination.AccessSharedAssets](../../../../requirements/interuss/automated_testing/coordination.md)**.

### Ensure clean workspace test step

#### [Clean any existing OIRs with known test IDs](clean_workspace_op_intents.md)

#### [Clean any existing subscriptions with known test IDs](clean_workspace_subs.md)

### Verify secondary DSS instances are clean test step

This test step queries all secondary instances to confirm that none of the test IDs that are used in the scenario exist.

#### [Verify secondary DSS contains no OIRs with a test ID](./fragments/oir/verify_clean_secondary_workspace.md)

#### [Verify secondary DSS contains no Subscriptions with a test ID](./fragments/sub/verify_clean_secondary_workspace.md)

## Subscription deletion is reflected on all DSS instances test case

This test case verifies that after a subscription is deleted from a DSS instance, it cannot be retrieved from any other
DSS instance.

### Create a subscription at every DSS in sequence test step

This test step will create a new subscription at every DSS, in sequence.

Note that this step is run once for each involved DSS (that is, once for the primary DSS and once for every secondary DSS)

#### [Create subscription on a DSS instance](./fragments/sub/crud/create_query.md)

Check that the subscription creation succeeds.

### Delete a subscription at every DSS in sequence test step

This test step will delete the freshly created subscription at every DSS, in sequence.
It then verifies that the subscription has been deleted from all DSS instances.

Note that this step is run once for each involved DSS (that is, once for the primary DSS and once for every secondary DSS)

#### [Delete subscription on a DSS instance](./fragments/sub/crud/delete_query.md)

Check that the subscription deletion succeeds.

#### [Get subscription query from all other DSS instances succeeds](./fragments/sub/crud/read_query.md)

Check that the subscription retrieval from all DSS instance succeeds.
It is expected to be not found, but that is validated in the check below.

#### 🛑 Subscription does not exist on all other DSS instances check

The subscription deleted on a DSS instance must have been removed from all other DSS instances.

If the subscription still exists on one of the other DSS instances, one of the instances fails to comply with **[astm.f3548.v21.DSS0210,A2-7-2,5a](../../../../requirements/astm/f3548/v21.md)**.


## OIR creation and modification does not trigger relevant notifications after subscription deletion test case

This test case verifies that after a subscription is deleted, newly created or modified OIRs will not receive the
relevant subscriptions to notify from the DSS instance, regardless of which instance was used to create or modify the
entity.

### Create an OIR at every DSS in sequence test step

This test step will create an operational intent reference at every DSS, in sequence, each time verifying that the DSS
does not require notification for any previously deleted subscription that intersects with the newly created OIR.

Note that this step is run once for each involved DSS (that is, once for the primary DSS and once for every secondary DSS)

#### [Create OIR](./fragments/oir/crud/create_query.md)

Check that the OIR creation query succeeds.

#### 🛑 DSS response does not contain the deleted subscriptions check

The response from a DSS to a valid OIR creation request is expected to contain any relevant subscription for the OIR's
extents. This does not include subscriptions deleted earlier.

If the DSS includes a deleted subscription, it fails to implement **[astm.f3548.v21.DSS0210,A2-7-2,5b](../../../../requirements/astm/f3548/v21.md)**.

### Modify an OIR at every DSS in sequence test step

This test step will modify an operational intent reference at every DSS, in sequence, each time verifying that the DSS
does not require notification for any previously deleted subscription that intersects with the modified OIR.

Note that this step is run once for each involved DSS (that is, once for the primary DSS and once for every secondary DSS)

#### [Modify OIR](./fragments/oir/crud/update_query.md)

Check that the OIR modification query succeeds.

#### 🛑 DSS response does not contain the deleted subscriptions check

The response from a DSS to a valid OIR modification request is expected to contain any relevant subscription for the
OIR's extents. This does not include subscriptions deleted earlier.

If the DSS includes a deleted subscription, it fails to implement **[astm.f3548.v21.DSS0210,A2-7-2,5c](../../../../requirements/astm/f3548/v21.md)**.


## Cleanup

Cleanup is skipped when a coordinator is provided but exclusive access could not be acquired.

### [Clean any straggling OIRs with known test IDs](clean_workspace_op_intents_during_cleanup.md)

### [Clean any straggling subscriptions with known test IDs](clean_workspace_subs_during_cleanup.md)
