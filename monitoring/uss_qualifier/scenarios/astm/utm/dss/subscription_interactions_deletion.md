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

[`PlanningAreaResource`](../../../../resources/astm/f3548/v21/planning_area.py) describes the 3D volume in which subscriptions will be created.

### utm_client_identity

[`ClientIdentityResource`](../../../../resources/communications/client_identity.py) provides the identity that will be used to interact with the DSS.

## Setup test case

### [Ensure clean workspace test step](clean_workspace.md)

This step ensures that no subscriptions and OIRs with the known test IDs exists in the DSS deployment.


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


## [Cleanup](./clean_workspace.md)
