# ASTM SCD DSS: Subscription and entity interaction test scenario

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

## Setup test case

### Ensure clean workspace test step

#### [Clean any existing OIRs with known test IDs](clean_workspace_op_intents.md)

#### [Clean any existing subscriptions with known test IDs](clean_workspace_subs.md)

This step ensures that no subscriptions and OIRs with the known test IDs exists in the DSS deployment.

## OIR creation and modification trigger relevant notifications test case

This test case verifies that newly created or modified OIRs will receive the relevant subscriptions to notify from the DSS instance,
regardless of which instance was used to create the entity.

### [Create background subscription test step](./fragments/sub/crud/create_query.md)

Sets up the subscription that cover the planning area from 'now' to 20 minutes in the future, and which will be used as part of the interaction tests.

### Create an OIR at every DSS in sequence test step

This test step will create an operational intent reference and assorted subscription at every DSS, in sequence, each time verifying that the DSS
requires notifications for any previously established subscription that intersects with the newly created OIR.

Note that this step is run once for each involved DSS (that is, once for the primary DSS and once for every secondary DSS)

#### [Create OIR](./fragments/oir/crud/create_query.md)

Check that the OIR creation query succeeds

#### 🛑 DSS response contains the expected background subscription check

The response from a DSS to a valid OIR creation request is expected to contain any relevant subscription for the OIR's extents.
This includes the subscription created earlier, as it is designed to intersect with the OIRs being created.

If the DSS omits the intersecting subscription, it fails to implement **[astm.f3548.v21.DSS0210,A2-7-2,4b](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 DSS returns the implicit subscriptions from intersecting OIRs check

The response from a DSS to a valid OIR creation request is expected to contain any relevant subscription for the OIR's extents.
This includes any implicit subscription previously created on the DSS as part of a previously created OIR.

If the DSS omits any of the implicit subscriptions belonging to an OIR previously created on another DSS (which are designed to all intersect),
any of the DSSes at which an earlier OIR was created, or the DSS at which the current OIR has been created,
are in violation of **[astm.f3548.v21.DSS0210,A2-7-2,4b](../../../../requirements/astm/f3548/v21.md)**.

### Modify an OIR at every DSS in sequence test step

This test step will modify the previously created operational intent reference and assorted subscription at every DSS, in sequence, each time verifying that the DSS
requires notifications for any previously established subscription that intersects with the modified OIR.

Note that this step is run once for each involved DSS (that is, once for the primary DSS and once for every secondary DSS)

#### [Modify OIR](./fragments/oir/crud/update_query.md)

Check that the OIR modification query succeeds

#### 🛑 DSS response contains the expected background subscription check

The response from a DSS to a valid OIR modification request is expected to contain any relevant subscription for the OIR's extents.
This includes the subscription created earlier, as it is designed to intersect with the OIRs being modified.

If the DSS omits the intersecting subscription, it fails to implement **[astm.f3548.v21.DSS0210,A2-7-2,4c](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 DSS returns the implicit subscriptions from intersecting OIRs check

The response from a DSS to a valid OIR modification request is expected to contain any relevant subscription for the OIR's extents.
This includes any implicit subscription previously created on the DSS as part of a previously created OIR.

If the DSS omits any of the implicit subscriptions belonging to an OIR previously created over time range A on another DSS (which are designed to all intersect),
any of the DSSes at which an earlier OIR was created, or the DSS at which the current OIR has been modified,
are in violation of **[astm.f3548.v21.DSS0210,A2-7-2,4c](../../../../requirements/astm/f3548/v21.md)**.


## Subscription creation returns relevant OIRs test case

This test case checks that, when a newly created subscription intersects with an existing OIR and that the subscription is intended for operational intent references,
the DSS includes the relevant OIRs in the response to the creation.

### Create a subscription at every DSS in sequence test step

This test step will create a new subscription at every DSS, in sequence, each time verifying that the DSS
returns any OIRs that intersect with the newly created subscription.

Note that this step is run once for each involved DSS (that is, once for the primary DSS and once for every secondary DSS)

#### [Create subscription on a DSS instance](./fragments/sub/crud/create_query.md)

Check that the subscription creation succeeds.

#### 🛑 DSS response contains the expected OIRs check

The response from a DSS to a valid subscription creation request is expected to contain any relevant OIRs for the subscription's extents if the subscription had the `notify_for_op_intents` flag set to `true`.

If the DSS omits the intersecting OIR, it fails to comply with **[astm.f3548.v21.DSS0210,A2-7-2,4a](../../../../requirements/astm/f3548/v21.md)**.

#### [Get subscription query from all other DSS instances succeeds](./fragments/sub/crud/read_query.md)

#### 🛑 Subscription may be retrieved from all other DSS instances check

The subscription created on a DSS instance must be retrievable from all other DSS instances.

If the subscription does not exist on one of the other DSS instances, one of the instances fails to comply with **[astm.f3548.v21.DSS0210,A2-7-2,4a](../../../../requirements/astm/f3548/v21.md)**.


## Expiration of subscriptions removes them test case

This test case validates that expired subscriptions (created explicitly) are removed from all DSS instances.
To validate this requirement, the subscriptions that were previously created at each DSS instance are modified so that they expire shortly after the modification.
Then it is checked that all the associated subscriptions were removed from all the DSS instances by searching for them in their planning area.
Do note that they are not queried directly, as it is deemed acceptable for expired subscription that were not explicitly deleted to still be retrievable.

### Expire explicit subscriptions at every DSS in sequence test step

This test step will modify explicit subscriptions that were previously created at each DSS instance so that they expire shortly after the modification.

Note that this step is run once for each involved DSS (that is, once for the primary DSS and once for every secondary DSS)

#### [Modify subscription on a DSS instance so that it expires soon](./fragments/sub/crud/update_query.md)

Check that the subscription modifications succeed and wait for them to expire.

#### [Search for subscriptions from all other DSS instances succeeds](./fragments/sub/crud/search_query.md)

Check that query succeeds.

#### 🛑 Subscription does not exist on all other DSS instances check

The explicit subscription expired on a DSS instance must have been removed from all other DSS instances.

If the subscription still exists on one of the other DSS instances, one of the instances fails to comply with **[astm.f3548.v21.DSS0210,A2-7-2,4d](../../../../requirements/astm/f3548/v21.md)**.


## Cleanup

### [Clean any straggling OIRs with known test IDs](clean_workspace_op_intents.md)

### [Clean any straggling subscriptions with known test IDs](clean_workspace_subs.md)
