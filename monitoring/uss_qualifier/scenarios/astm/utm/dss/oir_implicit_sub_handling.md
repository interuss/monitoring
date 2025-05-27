# ASTM SCD DSS: Implicit Subscription handling test scenario

## Overview

Checks that implicit subscriptions are properly created, mutated and cleaned up.

## Resources

### dss

[`DSSInstanceResource`](../../../../resources/astm/f3548/v21/dss.py) to be tested in this scenario.

### id_generator

[`IDGeneratorResource`](../../../../resources/interuss/id_generator.py) providing the Subscription IDs for this scenario.

### planning_area

[`PlanningAreaResource`](../../../../resources/astm/f3548/v21/planning_area.py) describes the 3D volume in which subscriptions will be created.

### utm_client_identity

[`ClientIdentityResource`](../../../../resources/communications/client_identity.py) provides the identity that will be used to interact with the DSS.

## Setup test case

### Ensure clean workspace test step

#### [Clean any existing OIRs with known test IDs](clean_workspace_op_intents.md)

#### [Clean any existing subscriptions with known test IDs](clean_workspace_subs.md)

## Single OIR implicit subscription is removed upon OIR deletion test case

### Create an OIR with implicit subscription test step

This step creates an OIR with an implicit subscription and confirms that the subscription can be queried

#### [Create OIR](./fragments/oir/crud/create_query.md)

#### [Valid Implicit Subscription](./fragments/sub/implicit_create.md)

### Delete the OIR with implicit subscription test step

#### [Delete OIR](./fragments/oir/crud/delete_known.md)

#### 🛑 The implicit subscription was removed check

Upon deletion of an OIR that is associated to an implicit subscription, if the subscription has no other
associated OIRs, the DSS is expected to remove it.

If a query attempting to fetch the implicit subscription succeeds, it implies that the implicit subscription has not
been removed, and the DSS is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 After removal of the only created OIR, subscriptions should be as before its creation check

If, after the DSS is left in the same state as it was 'found' for an area, the subscriptions currently active do not correspond to the ones
that were present when the test case started, the DSS may be failing to properly implement **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**
or **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

## Implicit subscriptions always properly cover their OIR test case

This test case verifies that implicit subscriptions belonging to OIRs that are created, updated and deleted
are properly managed.

In particular, the scenario verifies that:
 - implicit subscriptions attached to an OIR always correctly cover the OIR after it was created or mutated;
 - implicit subscriptions are properly removed when they are no longer necessary.

### Create an OIR with implicit subscription test step

Create an OIR with which interactions will be tested and request an implicit
subscription to be created.

#### [Create OIR](./fragments/oir/crud/create_query.md)

#### [Valid Implicit Subscription](./fragments/sub/implicit_create.md)

### Create an overlapping OIR without any subscription test step

This step creates an OIR in the `ACCEPTED` state that overlaps with the previously created OIR:
it does not request the creation of an implicit subscription and does not attach the OIR to any subscription explicitly.

This step expects that the implicit subscription from the previously created OIR is mentioned in the response's notifications,
and that no new implicit subscription is created.

#### [Create OIR](./fragments/oir/crud/create_query.md)

#### 🛑 New OIR creation response contains previous implicit subscription to notify check

If the newly created OIR does not mention the implicit subscription from the previous OIR in its notifications,
the DSS is either improperly managing implicit subscriptions, or failing to report the subscriptions relevant to an OIR,
and therefore in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)** or **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)** respectively.

#### [No implicit subscription was attached](./fragments/oir/oir_has_no_subscription.md)

### Mutate OIR with implicit subscription to not overlap anymore test step

This step mutates the first OIR, which has an implicit subscription, to no longer overlap with the second OIR.

The mutation request does not specify an existing subscription, and provides the parameters required for the creation of an implicit subscription.

#### [Mutate OIR](./fragments/oir/crud/update_correct.md)

#### 🛑 The implicit subscription can be queried check

The implicit subscription attached to the mutated OIR should be able to be queried.

If it cannot, the DSS is either improperly managing implicit subscriptions for OIRs, or failing to report the subscriptions relevant to an OIR,
in which case the DSS is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)** or **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**, respectively.

#### [Correct temporal bounds](fragments/sub/implicit_correct_exact.md)

#### 🛑 Non-mutated implicit subscription is deleted check

If the DSS chose to create a new implicit subscription instead of updating the existing one, and the DSS did not remove the previous subscription,
the DSS is in violation of either **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)** or **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

### Create an OIR overlapping with the second OIR but not the first test step

This step creates a new OIR that only overlaps the OIR that has no implicit subscription,
and expects to not have to notify any subscription related to the OIRs created in this scenario.

#### [Create OIR](./fragments/oir/crud/create_query.md)

#### 🛑 Within a temporal frame not overlapping a newly created implicit subscription, subscriptions should be the same as at the start of the test case check

Within a geotemporal area that does not intersect with any of the implicit subscriptions that are left within the DSS,
the subscriptions returned for an OIR created within said area should correspond to the ones
that were present when the test case started.

Otherwise, the DSS may be failing to properly implement **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**
or **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

#### [No implicit subscription was attached](./fragments/oir/oir_has_no_subscription.md)

## Implicit subscriptions are properly deleted when required by OIR mutation test case

This test case verifies that implicit subscriptions are properly removed if they become unnecessary following the mutation of an OIR.

### Ensure clean workspace test step

<!-- TODO(Shastick): Why do we need to reclean the workspace at this point?  We already ensured it was clean before starting the test; don't we know exactly what happened in the test and therefore know that it's already clean (or something failed)?  If a previous test case created something that we don't need/want in later test cases, the original test case should clean up at the end of the test case. -->

#### [Clean any existing OIRs with known test IDs](clean_workspace_op_intents.md)

#### [Clean any existing subscriptions with known test IDs](clean_workspace_subs.md)

### Create two OIRs with implicit subscription test step

Creates two OIRs with an implicit subscription, which will then be replaced by an explicitly created subscription
and deleted by an update that requests no subscription, respectively.

#### [Create OIR](./fragments/oir/crud/create_query.md)

#### [Valid Implicit Subscription](./fragments/sub/implicit_create.md)

### Create a subscription test step

This test step creates a subscription that will be used to replace the implicit subscription that was created for an OIR.

#### [Create subscription](./fragments/sub/crud/create_query.md)

Check creation succeeds and response is correct.

### Update OIR with implicit subscription to use explicit subscription test step

This step updates the OIR to use the subscription that was created in the previous step,
and expects the previous implicit subscription to be removed.

#### [Mutate OIR](./fragments/oir/crud/update_query.md)

#### 🛑 Previously attached implicit subscription was deleted check

If the implicit subscription that was attached to the OIR is still present after the OIR is updated to use another subscription,
the DSS is failing to properly manage implicit subscriptions for OIRs, and is therefore in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

### Update OIR with implicit subscription to use no subscription test step

This step updates the OIR to not use any subscription, and expects the implicit subscription to be removed.

#### [Mutate OIR](./fragments/oir/crud/update_query.md)

#### 🛑 Previously attached implicit subscription was deleted check

If the implicit subscription that was attached to the OIR is still present after the OIR is updated to use another subscription,
the DSS is failing to properly manage implicit subscriptions for OIRs, and is therefore in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## Implicit subscriptions are expanded as needed test case

This test case checks that a DSS will properly expand an implicit subscription to cover an OIR that is being attached to it.

### Ensure clean workspace test step

<!-- TODO(Shastick): Why do we need to reclean the workspace at this point?  We already ensured it was clean before starting the test; don't we know exactly what happened in the test and therefore know that it's already clean (or something failed)?  If a previous test case created something that we don't need/want in later test cases, the original test case should clean up at the end of the test case. -->

#### [Clean any existing OIRs with known test IDs](clean_workspace_op_intents.md)

#### [Clean any existing subscriptions with known test IDs](clean_workspace_subs.md)

### Create an OIR with implicit subscription test step

Create an OIR with which interactions will be tested and request an implicit
subscription to be created.

#### [Create OIR](./fragments/oir/crud/create_query.md)

#### [Valid Implicit Subscription](./fragments/sub/implicit_create.md)

### Expand the OIR while keeping the same implicit subscription test step

Expand the previously created OIR's duration while explicitly specifying the implicit subscription that
was automatically created for it.

#### [Mutate OIR](./fragments/oir/crud/update_query.md)

#### 🛑 The implicit subscription can be queried check

The implicit subscription attached to the mutated OIR should be able to be queried.

If it cannot, the DSS is either improperly managing implicit subscriptions for OIRs, or failing to report the subscriptions relevant to an OIR,
in which case the DSS is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)** or **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**, respectively.

#### [Correct temporal bounds](fragments/sub/implicit_correct_cover.md)

Ensure that the attached implicit subscription has been expanded

## Existing implicit subscription can replace an OIR's explicit subscription test case

This test case verifies that an implicit subscription can be used to replace an explicit subscription attached to an OIR.

### Ensure clean workspace test step

Reset the workspace for this test case.

#### [Clean any existing OIRs with known test IDs](clean_workspace_op_intents.md)

#### [Clean any existing subscriptions with known test IDs](clean_workspace_subs.md)

### [Create an explicit subscription test step](./fragments/sub/crud/create_query.md)

Create an explicit subscription to be initially set on the first OIR created in this test case

### Create first OIR with an explicit subscription test step

Create an OIR bound to the explicit subscription created in the previous step.

#### [Create OIR](./fragments/oir/crud/create_query.md)

### Create second OIR with an implicit subscription test step

Create a second OIR with an implicit subscription, which will then be used in the next step.

#### [Create OIR](./fragments/oir/crud/create_query.md)

#### [Valid Implicit Subscription](./fragments/sub/implicit_create.md)

Confirm that an implicit subscription was created.

### Replace first OIR's explicit subscription with implicit subscription test step

Replace the first OIR's explicit subscription with the implicit one created in the previous step.

#### [Mutate OIR](./fragments/oir/crud/update_query.md)

Confirm that the query to replace the second OIR's explicit subscription with the second OIR's implicit subscription succeeds.

#### [First OIR is now attached to the specified implicit subscription](fragments/oir/oir_has_expected_subscription.md)

## Existing implicit subscription can be attached to OIR without subscription test case

This test case verifies that an implicit subscription can be attached to an OIR that is not currently attached to any subscription.

### Ensure clean workspace test step

Reset the workspace for this test case.

#### [Clean any existing OIRs with known test IDs](clean_workspace_op_intents.md)

#### [Clean any existing subscriptions with known test IDs](clean_workspace_subs.md)

### [Create OIR with no subscription test step](./fragments/oir/crud/create_query.md)

#### [OIR is not attached to an implicit subscription](./fragments/oir/oir_has_no_subscription.md)

### [Create second OIR with an implicit subscription test step](./fragments/oir/crud/create_query.md)

#### [An implicit subscription was created](./fragments/sub/implicit_create.md)

### Attach OIR without subscription to implicit subscription test step

Attach the first OIR to the implicit subscription created with the second OIR.

#### [Attach OIR to implicit subscription](./fragments/oir/crud/update_query.md)

### Confirm OIR is now attached to implicit subscription test step

Confirms that the DSS properly attached the first OIR to the implicit subscription created with the second OIR.

#### [Get OIR query](./fragments/oir/crud/read_query.md)

#### [First OIR is now attached to the specified implicit subscription](fragments/oir/oir_has_expected_subscription.md)

## Cleanup

### [Remove OIRs created during this test](clean_workspace_op_intents.md)

### [Remove subscriptions created during this test](clean_workspace_subs.md)

