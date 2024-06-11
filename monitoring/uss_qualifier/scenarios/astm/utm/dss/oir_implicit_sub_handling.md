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

### [Ensure clean workspace test step](clean_workspace.md)

This step ensures that no OIRs with the known test IDs exists in the DSS.

## Single OIR implicit subscription is removed upon OIR deletion test case

### Create an OIR with implicit subscription test step

This step creates an OIR with an implicit subscription and confirms that the subscription can be queried

#### [Create OIR](./fragments/oir/crud/create_query.md)

#### [Valid Implicit Subscription](./fragments/sub/implicit_create.md)

### Delete the OIR with implicit subscription test step

#### [Delete OIR](./fragments/oir/crud/delete.md)

#### 🛑 The implicit subscription was removed check

Upon deletion of an OIR that is associated to an implicit subscription, if the subscription has no other
associated OIRs, the DSS is expected to remove it.

If a query attempting to fetch the implicit subscription succeeds, it implies that the implicit subscription has not
been removed, and the DSS is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 After removal of the only created OIR, subscriptions should be as before its creation check

If, after the DSS is left in the same state as it was 'found' for an area, the subscriptions currently active do not correspond to the ones
that were present when the test case started, the DSS may be failing to properly implement **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**
or **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

## Implicit subscriptions are properly mutated upon OIR mutation test case

This test case verifies that implicit subscriptions belonging to OIRs that are created, updated and deleted
are properly managed.

In particular, the scenario verifies that implicit subscriptions:
 - are created or attached to an OIR that requires them
 - are mutated when the OIR they cover is updated
 - removed when the last OIR they are attached to is deleted

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

### Mutate OIR with implicit subscription to not overlap anymore test step

This step mutates the first OIR, which has an implicit subscription, to no longer overlap with the second OIR.

#### [Mutate OIR](./fragments/oir/crud/update_correct.md)

#### 🛑 The implicit subscription can be queried check

The implicit subscription attached to the mutated OIR should be able to be queried.

If it cannot, the DSS is either improperly managing implicit subscriptions for OIRs, or failing to report the subscriptions relevant to an OIR,
in which case the DSS is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)** or **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**, respectively.

#### [Correct temporal bounds](fragments/sub/implicit_correct.md)

#### 🛑 Non-mutated implicit subscription is deleted check

If the DSS chose to create a new implicit subscription instead of updating the existing one, and the DSS did not remove the previous subscription,
the DSS is in violation of either **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)** or **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.

### Create an OIR overlapping with the second OIR but not the first test step

This step creates a new OIR that only overlaps the OIR that has no implicit subscription,
and expects to not have to notify any subscription related to the OIRs created in this scenario.

#### [Create OIR](./fragments/oir/crud/create_query.md)

#### 🛑 Within a temporal frame not overlapping a newly created implicit subscription, subscriptions should be the same as at the start of the test case check

Within a geotemporal are that does not intersect with any of the implicit subscriptions that are left within the DSS,
the subscriptions returned for an OIR created within said area should correspond to the ones
that were present when the test case started.

Otherwise, the DSS may be failing to properly implement **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**
or **[astm.f3548.v21.DSS0005,5](../../../../requirements/astm/f3548/v21.md)**.


## [Cleanup](./clean_workspace.md)
