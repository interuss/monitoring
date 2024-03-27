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

### second_utm_auth

A `resources.communications.AuthAdapterResource` containing a second set of valid credentials for interacting with the DSS.

This second set of credentials is required to validate that the DSS properly synchronizes the manager of a subscription to other DSS instances.

The test designer should provide this second set of credentials when full testing of manager synchronization behavior is desired.

#### Credential requirements

In general, these test credentials may be in all points equal to the ones used by the `AuthAdapterResource` that is
provided to the `dss` resources above, except for the value contained in the `sub` claim of the token.

Note that most checks in this scenario will work if the second set of credentials is not provided.

##### Required scope

For the purpose of this scenario, the `second_utm_auth` resource must provide access to a token with at least the following scope:

* `utm.strategic_coordination`

##### Separate subject

Note that the subject (or 'sub' claim) of the token that will be obtained for this resource
MUST be different from the one of the `dss` resources mentioned above:
this will be verified at runtime, and the depending checks will not be run if this is not the case.

## Setup test case

### [Ensure clean workspace test step](../clean_workspace.md)

This step ensures that no subscriptions with the known test IDs exist in the DSS.

This includes the main test subscription used in this test, as well as the extra subscription
used for testing the `manager` field sync, if the test is configured to test for it.

## Subscription Synchronization test case

This test case create a subscription on the main DSS, and verifies that it is properly synchronized to the other DSS instances.

It then goes on to mutate and delete it, each time confirming that all other DSSes return the expected results.

### Create subscription validation test step

This test step creates multiple subscriptions with different combinations of the optional end and start time parameters.

All subscriptions are left on the DSS when this step ends, as they are expected to be present for the subsequent step.

#### [Create subscription](../fragments/sub/crud/create_correct.md)

Verify that a subscription can be created on the primary DSS.

#### [Validate subscription](../fragments/sub/validate/correctness.md)

Verify that the subscription returned by the DSS under test is properly formatted and contains the expected content.

### Query newly created subscription test step

Query the created subscription at every DSS provided in `dss_instances`.


#### [Subscription is synchronized](../fragments/sub/sync.md)

Confirm that the subscription that was just created is properly synchronized across all DSS instances.

#### [Get subscription](../fragments/sub/crud/read_correct.md)

Confirms that each DSS provides access to the created subscription,

#### [Search subscription](../fragments/sub/crud/search.md)

Confirms that each DSS returns the created subscription when searched for.

#### [Validate subscription](../fragments/sub/validate/correctness.md)

Verify that the subscription returned by every DSS is correctly formatted and corresponds to what was created earlier.

#### [Validate version](../fragments/sub/validate/non_mutated.md)

Verify that the version of the subscription returned by every DSS is as expected.

### Mutate subscription broadcast test step

This test step mutates the previously created subscription, by accessing the primary DSS, to verify that the update is propagated to all other DSSes.
Notably, it checks that the subscription version is updated, including for changes that are not directly visible, such as changing the subscription's footprint.

#### [Update subscription](../fragments/sub/crud/update.md)

Confirm that the subscription can be mutated.

#### [Validate subscription](../fragments/sub/validate/correctness.md)

Verify that the subscription returned by the DSS is properly formatted and contains the correct content.

#### [Validate version](../fragments/sub/validate/mutated.md)

Verify that the version of the subscription returned by the DSS has been updated.

### Query updated subscription test step

Query the updated subscription at every DSS provided in `dss_instances`.

#### [Subscription is synchronized](../fragments/sub/sync.md)

Confirm that the subscription that was just mutated is properly synchronized across all DSS instances.

#### [Get subscription](../fragments/sub/crud/read_correct.md)

Confirms that the subscription that was just mutated can be retrieved from any DSS.

#### [Search subscription](../fragments/sub/crud/search.md)

Confirms that the subscription that was just mutated can be searched for from any DSS.

#### [Validate subscription](../fragments/sub/validate/correctness.md)

Verify that the subscription returned by every DSS is correctly formatted and corresponds to what was mutated earlier.

#### [Validate version](../fragments/sub/validate/non_mutated.md)

Verify that the version of the subscription returned by every DSS is as expected.

### Mutate subscription on secondaries test step

This test step attempts to mutate the subscription on every secondary DSS instance (that is, instances through which the subscription has not been created) to confirm that such mutations are properly propagated to every DSS.

Note that this step is repeated for every secondary DSS instance.

#### 🛑 Subscription can be mutated on secondary DSS check

If the secondary DSS does not allow the subscription to be mutated, either the secondary DSS or the primary DSS are in violation of one or both of the following requirements:

**[astm.f3548.v21.DSS0210,1b](../../../../../requirements/astm/f3548/v21.md)**, if the `manager` of the subscription fails to be taken into account (either because the primary DSS did not propagated it, or because the secondary failed to consider it);
**[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**, if the secondary DSS fails to properly implement the API to mutate subscriptions.

#### 🛑 Subscription returned by a secondary DSS is valid and correct check

When queried for a subscription that was created via another DSS, a DSS instance is expected to provide a valid subscription.

If it does not, it might be in violation of **[astm.f3548.v21.DSS0005,5](../../../../../requirements/astm/f3548/v21.md)**.

#### [Update subscription](../fragments/sub/crud/update.md)

Confirm that the secondary DSS handles the update properly.

#### [Validate subscription](../fragments/sub/validate/correctness.md)

Verify that the subscription returned by the DSS is properly formatted and contains the correct content.

#### [Validate version is updated by mutation](../fragments/sub/validate/mutated.md)

Verify that the version of the subscription is updated after the mutation on the secondary.

### Verify mutation on all secondaries test step

This step verifies that the mutation of the subscription on a secondary instance, from the previous step, is properly propagated to every other DSS.

Note that this step is repeated for every secondary DSS instance.

#### [Subscription is synchronized](../fragments/sub/sync.md)

Confirm that the subscription that was just mutated is properly synchronized across all DSS instances.

#### [Get subscription](../fragments/sub/crud/read_correct.md)

Confirms that the subscription that was just mutated can be retrieved from any DSS, and that it has the expected content.

#### [Search subscription](../fragments/sub/crud/search.md)

Confirms that the subscription that was just mutated can be searched for from any DSS, and that it has the expected content.

#### [Validate subscription](../fragments/sub/validate/correctness.md)

Verify that the subscription returned by the DSS is properly formatted and contains the correct content.

#### [Validate version is as expected when read](../fragments/sub/validate/non_mutated.md)

Verify that when we are reading the subscription without mutating it, the version is as expected.

### Create subscription with different credentials test step

If the second set of credentials is provided, this test step will create a subscription using these credentials,
in order to prepare the next step that checks manager synchronization.

#### [Create subscription](../fragments/sub/crud/create_query.md)

Verify that a subscription can be created on the primary DSS using the separate set of credentials.

### Verify manager synchronization test step

If the second set of credentials is provided, checks that the manager of a subscription is properly synchronized across all DSS instances.

This is done by verifying that the main credentials are not able to delete the subscription via any of the secondary DSS instances.

#### ⚠️ Subscription deletion with different non-managing credentials on secondary DSS fails check

If the subscription can be deleted by a client which did not create it, via a DSS instance to which the subscription was synced
following its creation on the primary DSS, either one of the primary DSS or the DSS that accepted the deletion failed to properly broadcast, respectively take into account, the manage of the subscription,
and therefore violates **[astm.f3548.v21.DSS0210,1b](../../../../../requirements/astm/f3548/v21.md)**.

### Delete subscription on primary test step

Attempt to delete the subscription that was created on the primary DSS through the primary DSS in various ways,
and ensure that the DSS reacts properly.

This also checks that the subscription data returned by a successful deletion is correct.

#### [Delete subscription](../fragments/sub/crud/delete_correct.md)

Confirms that a subscription can be deleted.

#### [Validate subscription](../fragments/sub/validate/correctness.md)

Verify that the subscription returned by the DSS via the deletion is properly formatted and contains the correct content.

#### [Validate version](../fragments/sub/validate/non_mutated.md)

Verify that the version of the subscription returned by the DSS is as expected

### Query deleted subscription test step

Attempt to query and search for the deleted subscription in various ways

#### 🛑 DSS should not return the deleted subscription check

If a DSS returns a subscription that was previously successfully deleted from the primary DSS,
either one of the primary DSS or the DSS that returned the subscription is in violation of one of the following requirements:

**[astm.f3548.v21.DSS0210,1a](../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../requirements/astm/f3548/v21.md)**, if the DSS through which the subscription was deleted is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../requirements/astm/f3548/v21.md)**.

### Delete subscriptions on secondaries test step

Attempt to delete subscriptions that were created through the primary DSS via the secondary DSS instances.

#### [Delete subscription](../fragments/sub/crud/delete_correct.md)

Confirms that a subscription can be deleted from a secondary DSS

#### [Validate subscription](../fragments/sub/validate/correctness.md)

Verify that the subscription returned by the DSS via the deletion is properly formatted and contains the correct content.

#### [Validate version](../fragments/sub/validate/non_mutated.md)

Verify that the version of the subscription returned by the DSS is as expected

#### 🛑 DSS should not return the deleted subscription check

If a DSS returns a subscription that was previously successfully deleted from the primary DSS,
either one of the primary DSS or the DSS that returned the subscription is in violation of one of the following requirements:

**[astm.f3548.v21.DSS0210,1a](../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../requirements/astm/f3548/v21.md)**, if the DSS through which the subscription was deleted is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../requirements/astm/f3548/v21.md)**.

## [Cleanup](../clean_workspace.md)

This step ensures that no subscriptions with the known test IDs remain in the DSS by deleting them at this point if they do exist.

This includes the main test subscription used in this test, as well as the extra subscription
used for testing the `manager` field sync, if the test is configured to test for it.
