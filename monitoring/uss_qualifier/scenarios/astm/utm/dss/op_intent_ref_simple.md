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

### [Create an operational intent reference test step](./fragments/oir/crud/create_query.md)

Create an operational intent reference to be used in this scenario.

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

## [Cleanup](./clean_workspace.md)
