# ASTM SCD DSS: Operational Intent Reference Simple test scenario

## Overview

Verifies the behavior of a DSS for simple interactions pertaining to operational intent references.

## Resources

### dss

[`DSSInstanceResource`](../../../../resources/astm/f3548/v21/dss.py) the DSS instance through which entities are created, modified and deleted.

### id_generator

[`IDGeneratorResource`](../../../../resources/interuss/id_generator.py) providing the base entity ID for this scenario.

### client_identity

[`ClientIdentityResource`](../../../../resources/communications/client_identity.py) the client identity that will be used to create and update operational intent references.

### planning_area

[`PlanningAreaResource`](../../../../resources/astm/f3548/v21/planning_area.py) describes the 3D volume in which operational intent references will be created.

## Setup test case

### [Ensure clean workspace test step](./clean_workspace.md)

This step ensures that no entities with the known test IDs exists in the DSS.

### [Create a subscription test step](./fragments/sub/crud/create_query.md)

Create an explicit subscription to be used in this scenario.

## Validate explicit subscription on OIR creation test case

Ensures that the explicit subscription provided upon creation of an OIR is properly validated and attached to the OIR.

### Provide subscription not covering extent of OIR being created test step

This step verifies that an OIR cannot be created when an explicit subscription that does not cover the extent of the OIR is specified.

#### 🛑 Request to create OIR with too short subscription fails check

If the DSS under test allows the qualifier to create an OIR with an explicit subscription that does not cover the extent of the OIR,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**

### [Create an OIR with correct explicit subscription test step](./fragments/oir/crud/create_query.md)

When the provided subscription covers the extent of the OIR, the OIR can be created.

#### [OIR is attached to expected subscription](./fragments/oir/oir_has_expected_subscription.md)

This step verifies that the OIR is attached to the subscription provided upon creation.

## Validate explicit subscription upon subscription replacement test case

Ensures that when the explicit subscription tied to an OIR is replaced with another explicit subscription,
this subscription is properly validated and attached to the OIR.

### [Create a subscription test step](./fragments/sub/crud/create_query.md)

Create an additional explicit subscription to be used in this test case.

### Attempt to replace OIR's existing explicit subscription with an insufficient one test step

This step verifies that an OIR's existing explicit subscription cannot be replaced with an explicit subscription that does not cover the extent of the OIR.

#### 🛑 Request to mutate OIR while providing a too short subscription fails check

If the DSS under test allows the qualifier to replace an OIR's existing explicit subscription with an explicit subscription that does not cover the extent of the OIR,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**

#### [OIR is attached to expected subscription](./fragments/oir/oir_has_expected_subscription.md)

Verify that the OIR is still attached to the previous, valid, subscription.

### [Replace the OIR's explicit subscription test step](./fragments/oir/oir_subscription_update.md)

This step verifies that an OIR attached to an explicit subscription can be mutated in order to be attached
to another explicit subscription that properly covers the extent of the OIR.

## Deletion requires correct OVN test case

Ensures that a DSS will only delete OIRs when the correct OVN is presented.

### [Ensure clean workspace test step](./clean_workspace.md)

This step resets the workspace for the present and following test cases by ensuring that no entities with the known test IDs exists in the DSS.

### [Create an operational intent reference test step](./fragments/oir/crud/create_query.md)

Create the operational intent reference that will be used for the deletion attempts that happen in the subsequent steps.

### Attempt deletion with missing OVN test step

This step verifies that an existing OIR cannot be deleted with a missing OVN.

#### 🛑 Request to delete OIR with empty OVN fails check

If the DSS under test allows the qualifier to delete an existing OIR with a request that provided an empty OVN,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**

### Attempt deletion with incorrect OVN test step

This step verifies that an existing OIR cannot be deleted with an incorrect OVN.

#### 🛑 Request to delete OIR with incorrect OVN fails check

If the DSS under test allows the qualifier to delete an existing OIR with a request that provided an incorrect OVN,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**

## Mutation requires correct OVN test case

Test DSS behavior when mutation requests are not providing the required OVN.

### Attempt mutation with missing OVN test step

This step verifies that an existing OIR cannot be mutated with a missing OVN.

#### 🛑 Request to mutate OIR with empty OVN fails check

If the DSS under test allows the qualifier to mutate an existing OIR with a request that provided an empty OVN,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**

### Attempt mutation with incorrect OVN test step

This step verifies that an existing OIR cannot be mutated with an incorrect OVN.

#### 🛑 Request to mutate OIR with incorrect OVN fails check

If the DSS under test allows the qualifier to mutate an existing OIR with a request that provided an incorrect OVN,
it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**

## [Cleanup](./clean_workspace.md)
