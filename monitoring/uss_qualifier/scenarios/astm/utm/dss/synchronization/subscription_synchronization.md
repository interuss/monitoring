# ASTM SCD DSS: Subscription Synchronization test scenario

## Overview

Verifies that all subscription CRUD operations performed on a single DSS instance are properly propagated to every other DSS

## Resources

### dss

[`DSSInstanceResource`](../../../../../resources/astm/f3548/v21/dss.py) the DSS instance through which entities are created, modified and deleted.

### other_instances

[`DSSInstancesResource`](../../../../../resources/astm/f3548/v21/dss.py) pointing to the DSS instances used to confirm that entities are properly propagated.

### id_generator

[`IDGeneratorResource`](../../../../../resources/interuss/id_generator.py) providing the Subscription ID for this scenario.

### planning_area

[`PlanningAreaResource`](../../../../../resources/astm/f3548/v21/planning_area.py) describes the 3D volume in which subscriptions will be created.

## Setup test case

### [Ensure clean workspace test step](../clean_workspace.md)

This step ensures that no subscription with the known test ID exists in the DSS.

## Subscription Synchronization test case

This test case create a subscription on the main DSS, and verifies that it is properly synchronized to the other DSS instances.

It then goes on to mutate and delete it, each time confirming that all other DSSes return the expected results.

### Create subscription validation test step

This test step creates multiple subscriptions with different combinations of the optional end and start time parameters.

All subscriptions are left on the DSS when this step ends, as they are expected to be present for the subsequent step.

#### [Create subscription](../fragments/subscription_crud.md)

Verify that a subscription can be created on the primary DSS.

#### [Validate subscription](../fragments/subscription_validate.md)

Verify that the subscription returned by the DSS under test is properly formatted and contains the expected content.

### Query newly created subscription test step

Query the created subscription at every DSS provided in `dss_instances`.

#### 🛑 Subscription returned by a secondary DSS is valid and correct check

When queried for a subscription that was created via another DSS, a DSS instance is expected to provide a valid subscription.

If it does not, it might be in violation of **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**.

#### [Subscription is synchronized](../fragments/subscription_sync.md)

Confirm that the subscription that was just created is properly synchronized across all DSS instances.

#### [Get subscription](../fragments/subscription_crud.md)

Confirms that each DSS provides access to the created subscription,

#### [Validate subscription](../fragments/subscription_validate.md)

Verify that the subscription returned by every DSS is correctly formatted and corresponds to what was created earlier.

### Mutate subscription test step

This test step mutates the previously created subscription to verify that the DSS reacts properly: notably, it checks that the subscription version is updated,
including for changes that are not directly visible, such as changing the subscription's footprint.

#### [Update subscription](../fragments/subscription_crud.md)

Confirm that the subscription can be mutated.

#### [Validate subscription](../fragments/subscription_validate.md)

Verify that the subscription returned by the DSS is properly formatted and contains the correct content.

### Query updated subscription test step

Query the updated subscription at every DSS provided in `dss_instances`.

#### 🛑 Subscription returned by a secondary DSS is valid and correct check

When queried for a subscription that was mutated via another DSS, a DSS instance is expected to provide a valid subscription.

If it does not, it might be in violation of **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**.

#### [Subscription is synchronized](../fragments/subscription_sync.md)

Confirm that the subscription that was just mutated is properly synchronized across all DSS instances.

#### [Get subscription](../fragments/subscription_crud.md)

Confirms that the subscription that was just mutated can be retrieved from any DSS.

#### [Validate subscription](../fragments/subscription_validate.md)

Verify that the subscription returned by every DSS is correctly formatted and corresponds to what was mutated earlier.

### Delete subscription test step

Attempt to delete the subscription in various ways and ensure that the DSS reacts properly.

This also checks that the subscription data returned by a successful deletion is correct.

#### [Delete subscription](../fragments/subscription_crud.md)

Confirms that a subscription can be deleted.

#### [Validate subscription](../fragments/subscription_validate.md)

Verify that the subscription returned by the DSS via the deletion is properly formatted and contains the correct content.

### Query deleted subscription test step

Attempt to query and search for the deleted subscription in various ways

#### 🛑 Secondary DSS should not return the deleted subscription check

If a DSS returns a subscription that was previously successfully deleted from the primary DSS,
either one of the primary DSS or the DSS that returned the subscription is in violation of **[astm.f3548.v21.DSS0210,1a](../../../../../requirements/astm/f3548/v21.md)**.

## [Cleanup](../clean_workspace.md)
