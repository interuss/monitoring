# ASTM SCD DSS: Subscription Validation test scenario

## Overview

Ensures that a DSS properly enforces limitations on created subscriptions

## Resources

### dss

[`DSSInstanceResource`](../../../../resources/astm/f3548/v21/dss.py) to be tested in this scenario.

### id_generator

[`IDGeneratorResource`](../../../../resources/interuss/id_generator.py) providing the Subscription ID for this scenario.

### planning_area

[`PlanningAreaResource`](../../../../resources/planning_area.py) describes the 3D volume in which subscriptions will be created.

## Setup test case

### Ensure clean workspace test step

#### [Clean any existing subscriptions with known test IDs](clean_workspace_subs.md)

## Subscription Validation test case

This test attempts to create subscriptions that should be rejected or adapted by the DSS.

### Subscription duration limitations test step

This test step attempts to create a subscription that exceeds the maximal subscription duration on the DSS.

It does so directly, by attempting to create a subscription that exceeds the maximal duration of `DSSMaxSubscriptionDuration` (24 hours),
and indirectly, by first creating a valid subscription and then attempting to mutate it to exceed the maximal duration.

#### 🛑 Accept a subscription of maximal duration check

If the DSS under test does not allow the creation of a subscription of the maximal allowed duration of `DSSMaxSubscriptionDuration`,
it is failing to create a subscription using valid parameters, and is thus failing to implement **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Don't create a too long subscription check

If the DSS under test does not reject a subscription that exceeds the maximal allowed duration of `DSSMaxSubscriptionDuration`,
or fails to truncate the duration of the subscription to this duration, it is in violation of **[astm.f3548.v21.DSS0015](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Don't mutate a subscription to be too long check

If the DSS under test does not reject a mutation that would cause a subscription to exceed the maximal allowed duration of `DSSMaxSubscriptionDuration`,
or fails to truncate the duration of the subscription to this duration, it is in violation of **[astm.f3548.v21.DSS0015](../../../../requirements/astm/f3548/v21.md)**.

## Cleanup

### [Clean any straggling subscriptions with known test IDs](clean_workspace_subs.md)
