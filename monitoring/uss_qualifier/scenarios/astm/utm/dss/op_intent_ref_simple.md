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

### Ensure clean workspace test step

#### [Clean any existing OIRs with known test IDs](clean_workspace_op_intents.md)

### Create an operational intent reference test step

#### [Create an operational intent reference to be used in this scenario.](./fragments/oir/crud/create_query.md)

## Deletion requires correct OVN test case

Ensures that a DSS will only delete OIRs when the correct OVN is presented.

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

## [Cleanup](./clean_workspace_op_intents.md)
