# ASTM SCD DSS: Subscription Simple test scenario

## Overview

Perform basic operations on a single DSS instance to create, update and delete subscriptions.

## Resources

### dss

[`DSSInstanceResource`](../../../../resources/astm/f3548/v21/dss.py) to be tested in this scenario.

### id_generator

[`IDGeneratorResource`](../../../../resources/interuss/id_generator.py) providing the Subscription IDs for this scenario.

### planning_area

[`PlanningAreaResource`](../../../../resources/astm/f3548/v21/planning_area.py) describes the 3D volume in which subscriptions will be created.

### problematically_big_area

[`VerticesResource`](../../../../resources/vertices.py) describing an area designed to be too big to be accepted by the DSS.

## Setup test case

### [Ensure clean workspace test step](clean_workspace.md)

This step ensures that no subscription with the known test ID exists in the DSS.

## Subscription Simple test case

This test case creates multiple subscriptions, goes on to query and search for them, then deletes and searches for them again.

### Create subscription validation test step

This test step creates multiple subscriptions with different combinations of the optional end and start time parameters.

All subscriptions are left on the DSS when this step ends, as they are expected to be present for the subsequent step.

#### 🛑 Create subscription check

As per **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**, the DSS API must allow callers to create a subscription with either onr or both of the
start and end time missing, provided all the required parameters are valid.

#### 🛑 Response to subscription creation contains a subscription check

As per **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**, upon creation of a subscription,
the newly created subscription must be part of its response.

#### [Validate subscription](./validate_subscription.md)

Verify that the subscription returned by the DSS after its creation is properly formatted and has the right content.

### Query Existing Subscription test step

Query and search for the created subscription in various ways

#### 🛑 Get Subscription by ID check

If the freshly created subscription cannot be queried using its ID, the DSS is failing to meet **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Search for all subscriptions in ISA area check

If the DSS fails to let us search in the area for which the subscription was just created, it is failing to meet **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Created Subscription is in search results check

If the created subscription is not returned in a search that covers the area it was created for, the DSS is not properly implementing **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 No huge search area allowed check

In accordance with **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**, the DSS should not allow searches for areas that are too big.

#### [Validate subscription](./validate_subscription.md)

Verify that the subscription returned by the DSS via the search is correctly formatted and corresponds to what was created earlier.

### Mutate Subscription test step

This test step mutates the previously created subscription to verify that the DSS reacts properly: notably, it checks that the subscription version is updated,
including for changes that are not directly visible, such as changing the subscription's footprint.

#### 🛑 Subscription can be mutated check

If a subscription cannot be modified with a valid set of parameters, the DSS is failing to meet **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Response to subscription mutation contains a subscription check

As per **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**, upon creation of a subscription,
the newly created subscription must be part of its response.

#### [Validate subscription](./validate_subscription.md)

Verify that the subscription returned by the DSS via the mutation is properly formatted and contains the correct content.

### Delete Subscription test step

Attempt to delete the subscription in various ways and ensure that the DSS reacts properly.

This also checks that the subscription data returned by a successful deletion is correct.

#### 🛑 Missing version prevents deletion check

An attempt to delete a subscription without providing a version should fail, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Incorrect version prevents deletion check

An attempt to delete a subscription while providing an incorrect version should fail, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Subscription can be deleted check

An attempt to delete a subscription when the correct version is provided should succeed, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### [Validate subscription](./validate_subscription.md)

Verify that the subscription returned by the DSS via the deletion is properly formatted and contains the correct content.

### Query Deleted Subscription test step

Attempt to query and search for the deleted subscription in various ways

#### 🛑 Query by subscription ID should fail check

If the DSS provides a successful reply to a direct query for the deleted subscription, it is in violation of **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Search for all subscriptions in ISA area check

If the DSS fails to let us search in the area for which the subscription was just created, it is failing to meet **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Deleted subscription should not be present in search results check

If the DSS returns the deleted subscription in a search that covers the area it was originally created for, the DSS is not properly implementing **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

## [Cleanup](./clean_workspace.md)
