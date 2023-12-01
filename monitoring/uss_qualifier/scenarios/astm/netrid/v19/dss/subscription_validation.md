# ASTM NetRID DSS: Subscription Validation test scenario

## Overview

Perform basic operations on a single DSS instance to create subscriptions and check that limitations are respected

## Resources

### dss

[`DSSInstanceResource`](../../../../../resources/astm/f3411/dss.py) to be tested in this scenario.

### id_generator

[`IDGeneratorResource`](../../../../../resources/interuss/id_generator.py) providing the Subscription IDs for this scenario.

### isa

[`ServiceAreaResource`](../../../../../resources/netrid/service_area.py) describing a service area for which to subscribe.

## Setup test case

### [Ensure clean workspace test step](test_steps/clean_workspace.md)

This step ensures that we remove any subscription that may already exist for the service area.  First, the DSS is queried for any applicable existing subscriptions, and then any subscriptions found are deleted.

## Subscription quantity limitations test case

### Create maximum number of subscriptions test step

The test will attempt to create 10 identical subscriptions for the same area and expect this to succeed.

#### Create up to the maximum allowed number of subscriptions in an area check

As per **[astm.f3411.v19.DSS0030,c](../../../../../requirements/astm/f3411/v19.md)**, the DSS API is expected to allow us
to create multiple subscriptions.

### Exceed maximum number of subscriptions test step

Now, create an 11th one and expect it to fail.

#### Enforce maximum number of subscriptions for an area check

If the DSS successfully creates an 11th Subscription in the same area instead of rejecting it,
it will not have performed the Subscription count validation as defined in **[astm.f3411.v19.DSS0050](../../../../../requirements/astm/f3411/v19.md)**

### Clean up subscriptions test step

Clean up any subscriptions created.

#### Successful subscription search query check

If the query for subscriptions fails, **[astm.f3411.v19.DSS0030,f](../../../../../requirements/astm/f3411/v19.md)** was not met.

#### Subscription can be deleted check

If the deletion attempt fails, **[astm.f3411.v19.DSS0030,d](../../../../../requirements/astm/f3411/v19.md)** was not met.

## Subscription duration limitations test case

### Try to create too-long subscription test step

The test will attempt to create a subscription for 24 hours and 10 minutes, and expect this to fail with an HTTP 400 error.

#### Too-long subscription creation rejected check

**[astm.f3411.v19.DSS0060](../../../../../requirements/astm/f3411/v19.md)** any subscription to the DSS may not exceed NetDSSMaxSubscriptionDuration (24 hours).

If creation of the too-long-duration subscription succeeds, the test expects that the effectively created subscription has been truncated to 24 hours, with a tolerance of minus 1 minute.

### Try to extend subscription test step

The test will attempt to create a valid subscription of 23 hours and 59 minutes, and then increase its duration to 24 hours and 10 minutes,
expecting this update to fail.

#### Valid subscription created check

The ability to create a valid subscription is required in **[astm.f3411.v19.DSS0030,c](../../../../../requirements/astm/f3411/v19.md)**.

#### Subscription duration limited during update check

If the DSS allows a user to extend an existing, valid subscription to a duration exceeding that specified in **[astm.f3411.v19.DSS0060](../../../../../requirements/astm/f3411/v19.md)**, this check will fail.

### Remove subscription test step

To clean up after itself, the test deletes the subscription created in the previous step.

#### Subscription deleted check

The ability to delete an existing subscription is required in **[astm.f3411.v19.DSS0030,d](../../../../../requirements/astm/f3411/v19.md)**.

## Cleanup

The cleanup phase of this test scenario will remove any subscription that may have been created during the test and that intersects with the test ISA.

### Successful subscription search query check

If the query for subscriptions fails, the "GET Subscriptions" portion of **[astm.f3411.v19.DSS0030,f](../../../../../requirements/astm/f3411/v19.md)** was not met.

### Subscription can be deleted check

If the deletion attempt fails, the "DELETE Subscription" portion of **[astm.f3411.v19.DSS0030,d](../../../../../requirements/astm/f3411/v19.md)** was not met.
