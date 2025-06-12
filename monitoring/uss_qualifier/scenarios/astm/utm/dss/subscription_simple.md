# ASTM SCD DSS: Subscription Simple test scenario

## Overview

Perform basic operations on a single DSS instance to create, update and delete subscriptions.

## Resources

### dss

[`DSSInstanceResource`](../../../../resources/astm/f3548/v21/dss.py) to be tested in this scenario.

### id_generator

[`IDGeneratorResource`](../../../../resources/interuss/id_generator.py) providing the Subscription IDs for this scenario.

### planning_area

[`PlanningAreaResource`](../../../../resources/planning_area.py) describes the 3D volume in which subscriptions will be created.

### problematically_big_area

[`VerticesResource`](../../../../resources/vertices.py) describing an area designed to be too big to be accepted by the DSS.

## Setup test case

### Ensure clean workspace test step

#### [Clean any existing subscriptions with known test IDs](clean_workspace_subs.md)

## Subscription Simple test case

This test case creates multiple subscriptions, goes on to query and search for them, then deletes and searches for them again.

### Create subscription validation test step

This test step creates multiple subscriptions with different combinations of the optional end and start time parameters.

All subscriptions are left on the DSS when this step ends, as they are expected to be present for the subsequent step.

#### [Create subscription](./fragments/sub/crud/create_correct.md)

Check creation succeeds and response is correct.

#### [Validate subscription](fragments/sub/validate/correctness.md)

Verify that the subscription returned by the DSS after its creation is properly formatted and has the right content.

### Query Existing Subscription test step

Query and search for the created subscription in various ways

#### 🛑 Get subscription query succeeds check

If the query to get an existing subscription fails, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Get subscription response is correct check

A successful get subscription query is expected to return a well-defined body, the content of which reflects the created subscription.
If the format and content of the response are not conforming, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Get subscription response format conforms to spec check

The response to a successful get subscription query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Search for all subscriptions in planning area query succeeds check

If the search query for the area for which the subscription was just created fails, it is failing to meet **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Search for all subscriptions in planning area response is correct check

A successful search query is expected to return a well-defined body, the content of which reflects the created subscription as well as any other subscription in the area.
If the format and content of the response are not conforming, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Search subscriptions response format conforms to spec check

The response to a successful subscription search query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Created Subscription is in search results check

If the created subscription is not returned in a search that covers the area it was created for, the DSS is not properly implementing **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 No huge search area allowed check

In accordance with **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**, the DSS should not allow searches for areas that are too big.

#### [Validate subscription](fragments/sub/validate/correctness.md)

Verify that the subscription returned by the DSS via the search is correctly formatted and corresponds to what was created earlier.

#### [Validate version field](fragments/sub/validate/non_mutated.md)

Verify that the version field is as expected.

### Attempt Subscription mutation with incorrect version test step

This test step attempts to mutate the subscription both with a missing and incorrect OVN, and checks that the DSS reacts properly.

#### 🛑 Mutation with empty version fails check

If a request to mutate a subscription is missing the version and succeeds, the DSS is failing to properly implement **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Mutation with incorrect version fails check

If a request to mutate a subscription providing the wrong version succeeds, the DSS is failing to properly implement **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

### Mutate Subscription test step

This test step mutates the previously created subscription to verify that the DSS reacts properly: notably, it checks that the subscription version is updated,
including for changes that are not directly visible, such as changing the subscription's footprint.

#### 🛑 Mutate subscription query succeeds check

If the query to mutate a subscription with valid parameters is not successful, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Mutate subscription response is correct check

A successful subscription mutation query is expected to return a well-defined body, the content of which reflects the newly defined subscription.
If the format and content of the response are not conforming, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Mutate subscription response format conforms to spec check

The response to a successful subscription mutation query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### [Validate subscription](fragments/sub/validate/correctness.md)

Verify that the subscription returned by the DSS via the mutation is properly formatted and contains the correct content.

#### [Validate version field](fragments/sub/validate/mutated.md)

Verify that the version field has been mutated.

### Delete Subscription test step

Attempt to delete the subscription in various ways and ensure that the DSS reacts properly.

This also checks that the subscription data returned by a successful deletion is correct.

#### 🛑 Missing version prevents deletion check

An attempt to delete a subscription without providing a version should fail, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Incorrect version prevents deletion check

An attempt to delete a subscription while providing an incorrect version should fail, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Delete subscription query succeeds check

If the query to delete an existing subscription fails, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Delete subscription response is correct check

A successful delete subscription query is expected to return a well-defined body, the content of which reflects the content of the subscription before deletion.
If the format and content of the response are not conforming, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### ⚠️ Delete subscription response format conforms to spec check

The response to a successful delete subscription query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Subscription can be deleted check

An attempt to delete a subscription when the correct version is provided should succeed, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### [Validate subscription](fragments/sub/validate/correctness.md)

Verify that the subscription returned by the DSS via the deletion is properly formatted and contains the correct content.

#### [Validate version field](fragments/sub/validate/non_mutated.md)

Verify that the version field is as expected.

### Query Deleted Subscription test step

Attempt to query and search for the deleted subscription in various ways

#### 🛑 Query by subscription ID should fail check

If the DSS provides a successful reply to a direct query for the deleted subscription, it is in violation of **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Search for all subscriptions in planning area query succeeds check

If the DSS fails to let us search in the area for which the subscription was just created, it is failing to meet **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Deleted subscription should not be present in search results check

If the DSS returns the deleted subscription in a search that covers the area it was originally created for, the DSS is not properly implementing **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

## Cleanup

### [Clean any straggling subscriptions with known test IDs](clean_workspace_subs.md)
