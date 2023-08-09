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

### Ensure clean workspace test step

This step ensures that we remove any subscription that may already exist for the service area.

#### Successful subscription query and cleanup check

We expect to be allowed ro query for existing subscriptions in order to clean them up

## Subscription limitations test case

### Subscription limitations test step

#### Enforce maximum number of subscriptions for an area check

**[astm.f3411.v22a.DSS0050](../../../../../requirements/astm/f3411/v22a.md)** for a given area for which the DSS is responsible, there may be at most NetDSSMaxSubscriptionPerArea (10) subscriptions per USS.

The test will attempt to create 10 subscriptions for the same area and expect this to succeed, then create an 11th one and expect it to fail.

#### Enforce maximum duration of subscriptions for an area check

**[astm.f3411.v22a.DSS0060](../../../../../requirements/astm/f3411/v22a.md)** any subscription to the DSS may not exceed NetDSSMaxSubscriptionDuration (24 hours).

The test will attempt to create a subscription for 24 hours and 10 minutes, and expect this to fail with an HTTP 400 error.

If the creation succeeds, the test expects that the effectively created subscription has been truncated to 24 hours, with a tolerance of minus 1 minute.

It will also attempt to create a valid subscription of 23 hours an 59 minutes, and then increase its duration to 24 hours and 10 minutes,
expecting this update to fail.

## Cleanup

### Successful subscription query and cleanup check

The cleanup phase of this test scenario will remove any subscription that may have been created during the test and that intersects with the test ISA.
