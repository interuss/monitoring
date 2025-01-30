# ASTM NetRID Service Provider operator notification under slow update rate test scenario

## Overview

This scenario evaluates Service Provider (SP) behavior in situations where a networked UAS is not sending telemetry at the required rate.

The SP is expected to properly notify the operator.

## Resources

### flights_data

A [`FlightDataResource`](../../../../resources/netrid/flight_data.py) containing 1 nominal flight per SP under test. Note that trimming the telemetry down to 0.5Hz happens in the scenario implementation.

The flights should be at least over one minute in length (telemetry is injected for a total duration of at least 61 seconds).

### service_providers

A set of [`NetRIDServiceProviders`](../../../../resources/netrid/service_providers.py) to be tested via the injection of RID flight data.  This scenario requires at least one SP under test.

### evaluation_configuration

This [`EvaluationConfigurationResource`](../../../../resources/netrid/evaluation.py) defines how to gauge success when observing the injected flights.


## Slow updates flight test case

This test case injects a flight that only has telemetry for every other second (it simulates sending updates at 0.5Hz instead of the required 1Hz).

This test case makes the following assumptions on top of requirement NET0040:

* if a UAS is not disconnected, the requirement of having an update frequency of 1Hz for 20% of the time applies to a sliding window of 1 minute.
* A UAS is deemed disconnected if it has not sent any data for 1 minute.

Concretely, the test case will expect that, if for a whole minute, a flight only has telemetry sent at 0.5hz, the SP will notify the operator.

### Establish notification baseline test step

This test step queries the `user_notification` endpoint before the flight is injected to determine the existing notifications in the system under test.

#### ⚠️ Successful user notifications retrieval check

**[interuss.automated_testing.rid.injection.DeleteTestSuccess](../../../../requirements/interuss/automated_testing/rid/injection.md)**

#### 🛑 No notification sent since scenario start check

This scenario assumes that there are no other notifications being sent to the operator shortly before the flight injection.

If notifications are reported to have been sent after the scenario's start but before the flight's injection, the assumptions don't hold and the scenario cannot proceed.

### [Injection test step](../v19/fragments/flight_injection.md)

Inject flight with a 0.5Hz update rate

### [Service Provider polling test step](../v19/fragments/sp_polling.md)

Poll the service providers until all of them have generated a new notification to the operator.

#### [Validate injected flight](./fragments/flight_check.md)

#### [Validate injected flight details](./fragments/flight_details_check.md)

#### 🛑 Successful user notifications retrieval check

**[interuss.automated_testing.rid.injection.UserNotificationsSuccess](../../../../requirements/interuss/automated_testing/rid/injection.md)**

### Verify operator notification test step

Confirm that every service provider has returned a notification

#### ⚠️ Operator notification present check

**[astm.f3411.v19.NET0040](../../../../requirements/astm/f3411/v19.md)** requires that the Service Provider notifies the operator if a UAS is not sending telemetry at the proper rate.

`uss_qualifier` injected a flight that provided telemetry at a rate of 0.5Hz, which is expected to trigger a notification to the operator. If such a notification is not detected, the Service Provider will fail this requirement.

## Cleanup

The cleanup phase of this test scenario attempts to remove injected data from all SPs.

### ⚠️ Successful test deletion check

**[interuss.automated_testing.rid.injection.DeleteTestSuccess](../../../../requirements/interuss/automated_testing/rid/injection.md)**
