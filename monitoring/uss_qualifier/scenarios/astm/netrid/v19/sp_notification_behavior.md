# ASTM NetRID Service Provider notification behavior test scenario

## Overview

In this scenario, a single nominal flight is injected into each NetRID Service Provider (SP) under test, after a subscription was created on the DSS.

The SP is expected to properly notify the owner of the Subscription.

## Resources

### flights_data

A [`FlightDataResource`](../../../../resources/netrid/flight_data.py) containing 1 nominal flight per SP under test.

### service_providers

A set of [`NetRIDServiceProviders`](../../../../resources/netrid/service_providers.py) to be tested via the injection of RID flight data.  This scenario requires at least one SP under test.

### mock_uss

MockUSSResource for testing notification delivery.

### dss_pool

A [`DSSInstancesResource`](../../../../resources/astm/f3411/dss.py) from which a DSS will be picked and on which a Subscription will be created.

### id_generator

[`IDGeneratorResource`](../../../../resources/interuss/id_generator.py) providing the Subscription ID for this scenario.

## Setup test case

### [Clean workspace test step](./dss/test_steps/clean_workspace.md)

## Service Provider notification behavior test case

### Mock USS Subscription test step

Before injecting the test flights, a subscription is created on the DSS for the configured mock USS to allow it
to validate that the Service Providers under test correctly send out notifications.

#### 🛑 Subscription creation succeeds check

As per **[astm.f3411.v19.DSS0030,c](../../../../requirements/astm/f3411/v19.md)**, the DSS API must allow callers to create a subscription with either one or both of the
start and end time missing, provided all the required parameters are valid.

### [Injection test step](./fragments/flight_injection.md)

In this step, uss_qualifier injects a single nominal flight into each SP under test, usually with a start time in the future.  Each SP is expected to queue the provided telemetry and later simulate that telemetry coming from an aircraft at the designated timestamps.

### Validate Mock USS received notification test step

This test step verifies that the mock_uss for which a subscription was registered before flight injection properly received a notification from each Service Provider
at which a flight was injected.

#### [Get mock_uss interactions](../../../interuss/mock_uss/get_mock_uss_interactions.md)

#### ℹ️ Service Provider notification was received within delay check

This check validates that the notification from each Service Provider was received by the mock_uss within the specified delay.

ASTM F3411 V19 has no explicit requirement for this check, so triggering it will raise an informational warning.

This check will be triggered if it takes longer than 3 seconds between the injection of the flight and the notification being received by the mock_uss.

## Cleanup

The cleanup phase of this test scenario attempts to remove injected data from all SPs.

### ⚠️ Successful test deletion check

**[interuss.automated_testing.rid.injection.DeleteTestSuccess](../../../../requirements/interuss/automated_testing/rid/injection.md)**

### [Clean Subscriptions](./dss/test_steps/clean_workspace.md)

Remove all created subscriptions from the DSS.
