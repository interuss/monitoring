# ASTM SCD DSS: Constraint Reference Simple test scenario

## Overview

Verifies the behavior of a DSS for simple interactions pertaining to constraint references.

## Resources

### dss

[`DSSInstanceResource`](../../../../resources/astm/f3548/v21/dss.py) the DSS instance through which entities are created, modified and deleted.

### id_generator

[`IDGeneratorResource`](../../../../resources/interuss/id_generator.py) providing the base entity ID for this scenario.

### client_identity

[`ClientIdentityResource`](../../../../resources/communications/client_identity.py) the client identity that will be used to create and update constraint references.

### planning_area

[`PlanningAreaResource`](../../../../resources/astm/f3548/v21/planning_area.py) describes the 3D volume in which constraint references will be created.

## Setup test case

### [Ensure clean workspace test step](./clean_workspace.md)

This step ensures that no entities with the known test IDs exists in the DSS.

### [Create a constraint reference test step](./fragments/cr/crud/create_query.md)

This step creates the constraint reference to be used in this scenario.

## Deletion requires correct OVN test case

Ensures that an existing CR can only be deleted when the correct OVN is provided.

### Attempt deletion with missing OVN test step

This step verifies that an existing CR cannot be deleted with a missing OVN.

#### 🛑 Request to delete CR with empty OVN fails check

If the DSS under test allows the qualifier to delete an existing CR with a request that provided an empty OVN,
it is in violation of **[astm.f3548.v21.DSS0005,3](../../../../requirements/astm/f3548/v21.md)**

### Attempt deletion with incorrect OVN test step

This step verifies that an existing CR cannot be deleted with an incorrect OVN.

#### 🛑 Request to delete CR with incorrect OVN fails check

If the DSS under test allows the qualifier to delete an existing CR with a request that provided an incorrect OVN,
it is in violation of **[astm.f3548.v21.DSS0005,3](../../../../requirements/astm/f3548/v21.md)**

## Mutation requires correct OVN test case

Ensures that an existing CR can only be mutated when the correct OVN is provided.

### Attempt mutation with missing OVN test step

This step verifies that an existing CR cannot be mutated with a missing OVN.

#### 🛑 Request to mutate CR with empty OVN fails check

If the DSS under test allows the qualifier to mutate an existing CR with a request that provided an empty OVN,
it is in violation of **[astm.f3548.v21.DSS0005,3](../../../../requirements/astm/f3548/v21.md)**

### Attempt mutation with incorrect OVN test step

This step verifies that an existing CR cannot be mutated with an incorrect OVN.

#### 🛑 Request to mutate CR with incorrect OVN fails check

If the DSS under test allows the qualifier to mutate an existing CR with a request that provided an incorrect OVN,
it is in violation of **[astm.f3548.v21.DSS0005,3](../../../../requirements/astm/f3548/v21.md)**

## [Cleanup](./clean_workspace.md)
