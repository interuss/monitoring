# ASTM NetRID DSS: ISA Subscription Interactions test scenario

## Overview

Verifies that interactions between ISAs and subscriptions happen as expected.

## Resources

### dss

[`DSSInstanceResource`](../../../../../resources/astm/f3411/dss.py) to be tested in this scenario.

### id_generator

[`IDGeneratorResource`](../../../../../resources/interuss/id_generator.py) providing the ISA ID for this scenario.

### isa

[`ServiceAreaResource`](../../../../../resources/netrid/service_area.py) describing an ISA to be created.

## Setup test case

### [Ensure clean workspace test step](test_steps/clean_workspace.md)

This scenario creates an ISA with a known ID. This step ensures that the ISA does not exist when the main part of the test starts.

Any previously created subscriptions for the test ISA's area that might still exist will be deleted.

## ISA Subscription Interactions test case

This test case will do the following, using the DSS being tested:

1. Create an ISA with the configured footprint,
2. Do several variants of creating and possibly mutating a subscription, either in or close to the ISA's area, and expect:
   - to find the created ISA mentioned in the reply
   - the notification index of the subscription to be 0
3. Modify the ISA, and expect:
   - to find the created subscription in the reply
   - the notification index of the subscription to be greater than 0
4. Delete the ISA, and expect:
   - to find the created subscription in the reply
   - the notification index of the subscription to be greater than it was after the mutation
5. Delete the subscription.

### New Subscription within ISA test step

This test step checks for interactions between ISAs and a subscription that is created within the ISA, then
subsequently mutated to only barely intersect with the ISA.

#### Create an ISA check

If the ISA cannot be created, the PUT DSS endpoint in **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)** is likely not implemented correctly.

#### Create a subscription within the ISA footprint check

The DSS should allow the creation of a subscription within the ISA footprint, otherwise it is in violation of **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)**

#### Subscription for the ISA's area mentions the ISA check

A subscription that is created for a volume that intersects with the previously created ISA should mention
the previously created ISA. If not, the serving DSS is in violation of **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)**.

#### Newly created subscription has a notification_index of 0 check

A newly created subscription is expected to have a notification index of 0, otherwise the DSS implementation under
test does not comply with **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)**

#### Mutate the ISA check

If the ISA cannot be mutated, **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)** is likely not implemented correctly.

#### Response to the mutation of the ISA contains subscription ID check

When an ISA is mutated, the DSS must return the identifiers for any subscription that was made to the ISA,
or be in violation of **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)**.

#### Subscription to an ISA has its notification index incremented after mutation check

When an ISA is mutated, the DSS must increment the notification index of any subscription to that ISA,
and return the up-to-date subscription in the response to the query mutating the ISA.

Failure to do so means that the DSS is not properly implementing **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)**.

#### Delete the ISA check

If that ISA cannot be deleted, the **[astm.f3411.v22a.DSS0030,d](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the ISA deletion endpoint might not be met.

#### Response to the deletion of the ISA contains subscription ID check

When an ISA is deleted, the DSS must return the identifiers for any subscription that was made to the ISA,
or be in violation of **[astm.f3411.v22a.DSS0030,b](../../../../../requirements/astm/f3411/v22a.md)**.

#### Subscription to an ISA has its notification index incremented after deletion check

When an ISA is deleted, the DSS must increment the notification index of any subscription to that ISA,
and return the up-to-date subscription in the response to the query deleting the ISA.

Failure to do so means that the DSS is not properly implementing **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)**.

#### Subscription can be deleted check

**[astm.f3411.v22a.DSS0030,d](../../../../../requirements/astm/f3411/v22a.md)** requires the implementation of the DSS endpoint to allow callers to delete subscriptions they created.

#### Notified subscriber check

Notifications to any subscriber to the created ISA need to be successful.  If a notification cannot be delivered, then the **[astm.f3411.v22a.NET0730](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the POST ISAs endpoint isn't met.

### New subscription within ISA is mutated to ISA boundary test step

This test step checks for interactions between ISAs and a subscription that is created within the ISA and the mutated
to only barely overlap with the ISA.

#### Create an ISA check

If the ISA cannot be created, the PUT DSS endpoint in **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)** is likely not implemented correctly.

#### Create a subscription within the ISA footprint check

The DSS should allow the creation of a subscription within the ISA footprint, otherwise it is in violation of **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)**

#### Mutate the subscription towards the ISA boundary check

The DSS should allow a valid mutation of a subscription's area, otherwise it is in violation of **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)**

#### Subscription for the ISA's area mentions the ISA check

A subscription that is created for a volume that intersects with the previously created ISA should mention
the previously created ISA. If not, the serving DSS is in violation of **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)**.

#### Mutated subscription has a notification_index of 0 check

A newly created subscription is expected to have a notification index of 0, otherwise the DSS implementation under
test does not comply with **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)**

#### Mutate the ISA check

If the ISA cannot be mutated, **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)** is likely not implemented correctly.

#### Response to the mutation of the ISA contains subscription ID check

When an ISA is mutated, the DSS must return the identifiers for any subscription that was made to the ISA,
or be in violation of **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)**.

#### Subscription to an ISA has its notification index incremented after mutation check

When an ISA is mutated, the DSS must increment the notification index of any subscription to that ISA,
and return the up-to-date subscription in the response to the query mutating the ISA.

Failure to do so means that the DSS is not properly implementing **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)**.

#### Subscription that only barely overlaps the ISA contains the ISA check

A subscription that is created for a volume that only barely overlaps with the previously created ISA should still
contain the ISA in the reply from the server, otherwise the DSS does not comply with **[astm.f3411.v22a.DSS0030,c](../../../../../requirements/astm/f3411/v22a.md)**

#### Delete the ISA check

If that ISA cannot be deleted, the **[astm.f3411.v22a.DSS0030,d](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the ISA deletion endpoint might not be met.

#### Response to the deletion of the ISA contains subscription ID check

When an ISA is deleted, the DSS must return the identifiers for any subscription that was made to the ISA,
or be in violation of **[astm.f3411.v22a.DSS0030,b](../../../../../requirements/astm/f3411/v22a.md)**.

#### Subscription to an ISA has its notification index incremented after deletion check

When an ISA is deleted, the DSS must increment the notification index of any subscription to that ISA,
and return the up-to-date subscription in the response to the query deleting the ISA.

Failure to do so means that the DSS is not properly implementing **[astm.f3411.v22a.DSS0030,a](../../../../../requirements/astm/f3411/v22a.md)**.

#### Subscription can be deleted check

**[astm.f3411.v22a.DSS0030,d](../../../../../requirements/astm/f3411/v22a.md)** requires the implementation of the DSS endpoint to allow callers to delete subscriptions they created.

#### Notified subscriber check

Notifications to any subscriber to the created ISA need to be successful.  If a notification cannot be delivered, then the **[astm.f3411.v22a.NET0730](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the POST ISAs endpoint isn't met.

## Cleanup

The cleanup phase of this test scenario attempts to remove the ISA if the test ended prematurely while
also deleting any subscription it might have created for the ISA's area.

#### Successful ISA query check

**[interuss.f3411.dss_endpoints.GetISA](../../../../../requirements/interuss/f3411/dss_endpoints.md)** requires the implementation of the DSS endpoint enabling retrieval of information about a specific ISA; if the individual ISA cannot be retrieved and the error isn't a 404, then this requirement isn't met.

#### Removed pre-existing ISA check

If an ISA with the intended ID is already present in the DSS, it needs to be removed before proceeding with the test.  If that ISA cannot be deleted, then the **[astm.f3411.v22a.DSS0030,d](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the ISA deletion endpoint might not be met.

#### Notified subscriber check

When a pre-existing ISA needs to be deleted to ensure a clean workspace, any subscribers to ISAs in that area must be notified (as specified by the DSS).  If a notification cannot be delivered, then the **[astm.f3411.v22a.NET0730](../../../../../requirements/astm/f3411/v22a.md)** requirement to implement the POST ISAs endpoint isn't met.

#### Successful subscription search query check

**[astm.f3411.v22a.DSS0030,f](../../../../../requirements/astm/f3411/v22a.md)** requires the implementation of the DSS endpoint to allow callers to retrieve the subscriptions they created.

#### Subscription can be deleted check

**[astm.f3411.v22a.DSS0030,d](../../../../../requirements/astm/f3411/v22a.md)** requires the implementation of the DSS endpoint to allow callers to delete subscriptions they created.
