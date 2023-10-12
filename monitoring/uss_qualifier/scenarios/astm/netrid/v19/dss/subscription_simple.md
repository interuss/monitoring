# ASTM NetRID DSS: Subscription Simple test scenario

## Overview

Perform basic operations on a single DSS instance to create, update and delete subscriptions

## Resources

### dss

[`DSSInstanceResource`](../../../../../resources/astm/f3411/dss.py) to be tested in this scenario.

### id_generator

[`IDGeneratorResource`](../../../../../resources/interuss/id_generator.py) providing the Subscription IDs for this scenario.

### isa

[`ServiceAreaResource`](../../../../../resources/netrid/service_area.py) describing a service area for which to subscribe.

## Setup test case

### Ensure clean workspace test step

This step ensures that we remove any subscription that may already exist for the service area.  First, the DSS is queried for any applicable existing subscriptions, and then any subscriptions found are deleted.

#### Successful subscription query check

If the query for subscriptions fails, the "GET Subscriptions" portion of **[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** was not met.

#### Successful subscription deletion check

If the deletion attempt fails, the "DELETE Subscription" portion of **[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** was not met.

## Subscription Simple test case

### Subscription Simple test step

TODO

## Cleanup

The cleanup phase of this test scenario will remove any subscription that may have been created during the test and that intersects with the test ISA.

### Successful subscription query check

If the query for subscriptions fails, the "GET Subscriptions" portion of **[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** was not met.

### Successful subscription deletion

If the deletion attempt fails, the "DELETE Subscription" portion of **[astm.f3411.v19.DSS0030](../../../../../requirements/astm/f3411/v19.md)** was not met.
