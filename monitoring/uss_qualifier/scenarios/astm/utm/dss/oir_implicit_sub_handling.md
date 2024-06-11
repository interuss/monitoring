# ASTM SCD DSS: Implicit Subscription handling test scenario

## Overview

Verifies

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

#### 🛑 An implicit subscription was created and can be queried check

The creation of an operational intent in a geo-temporal volume for which the client has not yet established a subscription
is expected to trigger the creation of an implicit subscription.

If the DSS does not create the implicit subscription, it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

#### 🛑 Implicit subscription has correct temporal parameters check

If the implicit subscription time boundaries do not match the OIR's, either one, or both, of the following are possible:

The DSS is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**, as the implicit subscription does not cover the OIR's time boundaries;
Entities that should have been cleaned up earlier are still present in the DSS, and this scenario cannot proceed.

### Delete the OIR with implicit subscription test step

#### [Delete OIR](./fragments/oir/crud/delete.md)

#### 🛑 The implicit subscription was removed check

Upon deletion of an OIR that is associated to an implicit subscription, if the subscription has no other
associated OIRs, the DSS is expected to remove it.

If a query attempting to fetch the implicit subscription succeeds, it implies that the implicit subscription has not
been removed, and the DSS is in violation of **[astm.f3548.v21.DSS0005,1](../../../../requirements/astm/f3548/v21.md)**.

## Implicit subscriptions are mutated and reused when possible test case

This test case verifies that implicit subscriptions belonging to OIRs that are created, updated and deleted
are properly managed.

In particular, the scenario verifies that implicit subscriptions:
 - are created anew when existing implicit subscription cannot be reused
 - are reused and adapted when possible
 - removed when every OIR they cover is deleted.

TBC

## [Cleanup](./clean_workspace.md)
