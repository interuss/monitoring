# ASTM NetRID Service Provider operator notification under slow update rate test scenario

## Overview

This scenario evaluates Service Provider (SP) behavior in situations where a networked UAS is not sending telemetry at the required rate.

The SP is expected to properly notify the operator.

## Resources

### flights_data

A [`FlightDataResource`](../../../../resources/netrid/flight_data.py) containing 1 nominal flight per SP under test. Note that trimming the telemetry down to 0.5Hz happens in the scenario implementation.

### service_providers

A set of [`NetRIDServiceProviders`](../../../../resources/netrid/service_providers.py) to be tested via the injection of RID flight data.  This scenario requires at least one SP under test.

### evaluation_configuration

This [`EvaluationConfigurationResource`](../../../../resources/netrid/evaluation.py) defines how to gauge success when observing the injected flights.

### dss_pool

A dss from the pool will be used to determine the URL at which to query for flight information on the Service Provider under test.

## Slow updates flight test case

This test case injects a flight that only has telemetry for every other second (it simulates sending updates at 0.5Hz instead of the required 1Hz).

This test case makes the following assumptions on top of requirement NET0040:

* if a UAS is not disconnected, the requirement of having an update frequency of 1Hz for 20% of the time applies to a sliding window of 1 minute.
* A UAS is deemed disconnected if it has not sent any data for 1 minute.

Concretely, the test case will expect that, if for a whole minute, a flight only has telemetry sent at 0.5hz, the SP will notify the operator.

### [Injection test step](../v22a/fragments/flight_injection.md)

Inject flight with a 0.5Hz update rate

### Service Provider polling step

Wait for roughly a minute (while polling the SP to confirm the flight is still there) so the SP may realize the telemetry is not coming in at the required rate.

### Verify operator notification step

Query the user_notification endpoint to verify that the operator was notified of the slow update rate.

## Cleanup

The cleanup phase of this test scenario attempts to remove injected data from all SPs.

### ⚠️ Successful test deletion check

**[interuss.automated_testing.rid.injection.DeleteTestSuccess](../../../../requirements/interuss/automated_testing/rid/injection.md)**
