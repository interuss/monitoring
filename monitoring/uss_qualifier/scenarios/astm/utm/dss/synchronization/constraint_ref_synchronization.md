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

[`PlanningAreaResource`](../../../../../resources/astm/f3548/v21/planning_area.py) describes the 3D volume in which constraint reference will be created.

### client_identity

[`ClientIdentityResource`](../../../../../resources/communications/client_identity.py) to be used for this scenario.

## Setup test case

### [Ensure clean workspace test step](../clean_workspace.md)

This step ensures that no constraint reference with the known test ID exists in the DSS.

## CR synchronization test case

This test case creates an constraint reference on the main DSS, and verifies that it is properly synchronized to the other DSS instances.

It then goes on to mutate and delete it, each time confirming that all other DSSes return the expected results.

### Create CR validation test step

#### [Create CR](../fragments/cr/crud/create_correct.md)

Verify that an constraint reference can be created on the primary DSS.

#### [CR Content is correct](../fragments/cr/validate/correctness.md)

Verify that the constraint reference returned by the DSS under test is properly formatted and contains the expected content.

## [Cleanup](../clean_workspace.md)
