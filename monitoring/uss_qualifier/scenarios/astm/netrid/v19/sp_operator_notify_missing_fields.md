# ASTM NetRID Service Provider operator notification on missing fields test scenario

## Overview

This scenario evaluates Service Provider (SP) behavior in situations where a networked UAS is not sending all fields that are required to participate in Network Remote ID.

The SP is expected to properly notify the operator.

## Resources

### flights_data

A [`FlightDataResource`](../../../../resources/netrid/flight_data.py) containing 1 nominal flight per SP under test. Note that fields removal from the telemetry is performed by the scenario implementation.

### service_providers

A set of [`NetRIDServiceProviders`](../../../../resources/netrid/service_providers.py) to be tested via the injection of RID flight data. This scenario requires at least one SP under test.

### evaluation_configuration

This [`EvaluationConfigurationResource`](../../../../resources/netrid/evaluation.py) defines how to gauge success when observing the injected flights.

## Missing fields flight test case

This test case injects a flight that has a missing field and check that the operator is being notified. The test case is repeated for each mandatory field, so all of them will be tested.

### [Retrieve pre-existing operator notification test step](../v19/fragments/user_notification_retrieval.md)

Query the user_notification endpoint to list the current notifications.

### [Injection test step](../v19/fragments/flight_injection.md)

Inject a flight with one missing field, in the first telemetry frame of the flight. All fields are tested as the test case is run multiples time on each mandatory field, but only one field at a time will be missing.

### [Service Provider polling test step](../v19/fragments/user_notification_retrieval.md)

Poll service providers user_notification endpoint to verify that the operator was notified of the missing field by comparing the current notifications and the ones retrieved in the initial step

### Verify operator notification test step

Compare after polling the notification of each service providers retrieved during polling.

#### ⚠️ All injected flights have generated user notifications check

The "after" set of operator notifications should contain at least one more entry than the "before" set of operator notifications. If there was no new operator notification, the Service Provider will not have met **[astm.f3411.v19.NET0030](../../../../requirements/astm/f3411/v19.md)**.

### Intermediate cleanup test step

This step attempts to remove injected data from all SPs, avoiding multiple flights with the same data at the same time.

#### ⚠️ Successful test deletion check

**[interuss.automated_testing.rid.injection.DeleteTestSuccess](../../../../requirements/interuss/automated_testing/rid/injection.md)**

## Cleanup

The cleanup phase of this test scenario attempts to remove injected data from all SPs.

### ⚠️ Successful test deletion check

**[interuss.automated_testing.rid.injection.DeleteTestSuccess](../../../../requirements/interuss/automated_testing/rid/injection.md)**
