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

[`PlanningAreaResource`](../../../../resources/astm/f3548/v21/planning_area.py) describes the 3D volume in which subscriptions will be created.

### utm_client_identity

[`ClientIdentityResource`](../../../../resources/communications/client_identity.py) provides the identity that will be used to interact with the DSS.

## Setup test case

### [Ensure clean workspace test step](clean_workspace.md)

This step ensures that no subscriptions and OIRs with the known test IDs exists in the DSS deployment.

## OIR creation triggers relevant notifications test case

This test case verifies that newly created OIRs will receive the relevant subscriptions to notify from the DSS instance,
regardless of which instance was used to create the entity.

### [Create first background subscription test step](./fragments/sub/crud/create_query.md)

Sets up the first subscription that cover the planning area from 'now' to 20 minutes in the future, and which will be used as part of the interaction tests.

### [Create second background subscription test step](./fragments/sub/crud/create_query.md)

Sets up the second subscription that cover the planning area from 20 minutes after the first starts and that lasts for 1 hour, and which will be used as part of the interaction tests.

### Create an OIR at every DSS in sequence test step

This test step will create an operational intent reference and assorted subscription at every DSS, in sequence, each time verifying that the DSS
requires notifications for any previously established subscription that intersects with the newly created OIR.

Note that this step is run once for each involved DSS (that is, once for the primary DSS and once for every secondary DSS)

#### [Create OIR](./fragments/oir/crud/create_query.md)

Check that the OIR creation query succeeds

#### 🛑 DSS response contains the expected background subscription check

The response from a DSS to a valid OIR creation request is expected to contain any relevant subscription for the OIR's extents.
This includes one of the subscriptions created earlier, as it is designed to intersect with the OIRs being created.

If the DSS omits the intersecting subscription, it fails to implement **[astm.f3548.v21.DSS0210,A2-7-2,4b](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 DSS does not return non-intersecting background subscription check

The response from a DSS to a valid OIR creation request is expected to contain any relevant subscription for the OIR's extents.
This should exclude one of subscriptions created earlier, as it is designed to not intersect with the OIRs being created.

If the DSS includes the non-intersecting subscription, it fails to implement **[astm.f3548.v21.DSS0210,A2-7-2,4b](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 DSS returns the implicit subscriptions from intersecting OIRs check

The response from a DSS to a valid OIR creation request is expected to contain any relevant subscription for the OIR's extents.
This includes any implicit subscription previously created on the DSS as part of a previously created OIR.

If the DSS omits any of the implicit subscriptions belonging to an OIR previously created on another DSS (which are designed to all intersect),
any of the DSSes at which an earlier OIR was created, or the DSS at which the current OIR has been created,
are in violation of **[astm.f3548.v21.DSS0210,A2-7-2,4b](../../../../requirements/astm/f3548/v21.md)**.

## [Cleanup](./clean_workspace.md)
