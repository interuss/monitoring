# ASTM SCD DSS: Operational Intent Explicit Subscription handling test scenario

## Overview

Verifies the behavior of a DSS for interactions pertaining to operational intent references being attached to explicit subscriptions.

## Resources

### dss

[`DSSInstanceResource`](../../../../resources/astm/f3548/v21/dss.py) the DSS instance through which entities are created, modified and deleted.

### id_generator

[`IDGeneratorResource`](../../../../resources/interuss/id_generator.py) providing the base entity ID for this scenario.

### client_identity

[`ClientIdentityResource`](../../../../resources/communications/client_identity.py) the client identity that will be used to create and update operational intent references.

### planning_area

[`PlanningAreaResource`](../../../../resources/planning_area.py) describes the 3D volume in which operational intent references will be created.

## Setup test case

This test case ensures that no entities with the known test IDs exists in the DSS.

### [Cleanup OIRs test step](./clean_workspace_op_intents.md)

### [Cleanup Subscriptions test step](./clean_workspace_subs.md)

## Validate explicit subscription on OIR creation test case

Ensures that the explicit subscription provided upon creation of an OIR is properly validated and attached to the OIR.

### [Create independent subscription test step](./fragments/sub/crud/create_query.md)

### Provide subscription not covering extent of OIR being created test step

This step verifies that an OIR cannot be created when an explicit subscription that does not cover the extent of the OIR is specified.

#### 🛑 Request to create OIR with too short subscription fails check

If the DSS under test allows the qualifier to create an OIR with an explicit subscription that does not cover the extent of the OIR,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**

### Create an OIR with correct explicit subscription test step

When the provided subscription covers the extent of the OIR, the OIR can be created, and is then properly
attached to the specified subscription.

#### [OIR creation with a sufficient subscription is possible](./fragments/oir/crud/create_query.md)

### [OIR is attached to expected subscription test step](./fragments/oir/oir_has_expected_subscription.md)

## Validate explicit subscription upon subscription replacement test case

Ensures that when the explicit subscription tied to an OIR is replaced with another explicit subscription,
this subscription is properly validated and attached to the OIR.

### Create a subscription test step

Create an additional explicit subscription to be used in this test case.

#### [Create an additional explicit subscription](./fragments/sub/crud/create_query.md)

### Attempt to replace OIR's existing explicit subscription with an insufficient one test step

This step verifies that an OIR's existing explicit subscription cannot be replaced with an explicit subscription that does not cover the extent of the OIR.

#### 🛑 Request to mutate OIR while providing a too short subscription fails check

If the DSS under test allows the qualifier to replace an OIR's existing explicit subscription with an explicit subscription that does not cover the extent of the OIR,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**

### OIR is attached to expected subscription test step

#### [Unchanged OIR is attached to previous, valid, subscription](./fragments/oir/oir_has_expected_subscription.md)

### Replace the OIR's explicit subscription test step

This step verifies that an OIR attached to an explicit subscription can be mutated in order to be attached
to another explicit subscription that properly covers the extent of the OIR.

#### [Update the OIR's subscription](./fragments/oir/crud/update_query.md)

### OIR is attached to expected subscription test step

#### [Updated OIR is attached to newly specified subscription](./fragments/oir/oir_has_expected_subscription.md)

### Cleanup After Test Case test step

The test case that follows requires the creation of a fresh OIR and subscription. Therefore, this test case will clean up after itself.

#### [Delete OIRs](./fragments/oir/crud/delete_query.md)

#### [Delete Subscriptions](./fragments/sub/crud/delete_query.md)

## OIR in ACCEPTED state can be created without subscription test case

Checks that a DSS allows an OIR to be created in the accepted state without any subscription.

### Create an operational intent reference test step

This step verifies that an OIR can be created in the ACCEPTED state without providing any subscription information (implicit or explicit) in the request.

#### [Create OIR in ACCEPTED state without subscription](./fragments/oir/crud/create_query.md)

### [OIR is not attached to any subscription test step](./fragments/oir/oir_has_no_subscription.md)

## Validate explicit subscription being attached to OIR without subscription test case

Ensures that an explicit subscription can be attached to an OIR without subscription attached, and that the subscription is required to properly cover the OIR.

### [Create a subscription test step](./fragments/sub/crud/create_query.md)

### Attempt to attach insufficient subscription to OIR test step

This step verifies that the DSS refuses the request to attach an insufficient subscription to an OIR that currently has no subscription.

#### 🛑 Request to attach insufficient subscription to OIR fails check

If the DSS under test allows the qualifier to attach an insufficient explicit subscription to a subscription-free OIR,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**

### [OIR is not attached to any subscription test step](./fragments/oir/oir_has_no_subscription.md)

### Attach explicit subscription to OIR test step

#### [Attach OIR to sufficient explicit subscription](./fragments/oir/crud/update_query.md)

### [OIR is attached to expected subscription test step](./fragments/oir/oir_has_expected_subscription.md)

## Remove explicit subscription from OIR test case

Checks that an OIR in the ACCEPTED state that is attached to an explicit subscription can be mutated in order to not be attached to any subscription.

### [Remove explicit subscription from OIR test step](./fragments/oir/crud/update_query.md)

### [OIR is not attached to any subscription test step](./fragments/oir/oir_has_no_subscription.md)

## Cleanup

### [Cleanup OIRs test step](./clean_workspace_op_intents.md)

### [Cleanup Subscriptions test step](./clean_workspace_subs.md)
