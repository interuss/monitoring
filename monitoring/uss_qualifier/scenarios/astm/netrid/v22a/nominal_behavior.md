# ASTM NetRID nominal behavior test scenario

## Overview

In this scenario, a single nominal flight is injected into each NetRID Service Provider (SP) under test.  Each of the injected flights is expected to be visible to all the observers at appropriate times and for appropriate requests.

## Resources

### flights_data

A [`FlightDataResource`](../../../../resources/netrid/flight_data.py) containing 1 nominal flight per SP under test.

### service_providers

A set of [`NetRIDServiceProviders`](../../../../resources/netrid/service_providers.py) to be tested via the injection of RID flight data.  This scenario requires at least one SP under test.

### observers

A set of [`NetRIDObserversResource`](../../../../resources/netrid/observers.py) to be tested via checking their observations of the NetRID system and comparing the observations against expectations.  An observer generally represents a "Display Application", in ASTM F3411 terminology.  This scenario requires at least one observer.

### mock_uss

(Optional) MockUSSResource for testing notification delivery. If left unspecified, the scenario will not run any notification-related checks.

### evaluation_configuration

This [`EvaluationConfigurationResource`](../../../../resources/netrid/evaluation.py) defines how to gauge success when observing the injected flights.

### dss_pool

If specified, uss_qualifier will act as a Display Provider and check a DSS instance from this [`DSSInstanceResource`](../../../../resources/astm/f3411/dss.py) for appropriate identification service areas and then query the corresponding USSs with flights using the same session.

### id_generator

[`IDGeneratorResource`](../../../../resources/interuss/id_generator.py) providing the Subscription ID for this scenario.

## Setup test case

### [Clean workspace test step](./dss/test_steps/clean_workspace.md)

## Nominal flight test case

### Mock USS Subscription test step

Before injecting the test flights, a subscription is created on the DSS for the configured mock USS to allow it
to validate that Servie Providers under test correctly send out notifications.

#### Subscription creation succeeds check

As per **[astm.f3411.v22a.DSS0030,c](../../../../requirements/astm/f3411/v22a.md)**, the DSS API must allow callers to create a subscription with either onr or both of the
start and end time missing, provided all the required parameters are valid.

### Injection test step

In this step, uss_qualifier injects a single nominal flight into each SP under test, usually with a start time in the future.  Each SP is expected to queue the provided telemetry and later simulate that telemetry coming from an aircraft at the designated timestamps.

#### 🛑 Successful injection check

Per **[interuss.automated_testing.rid.injection.UpsertTestSuccess](../../../../requirements/interuss/automated_testing/rid/injection.md)**, the injection attempt of the valid flight should succeed for every NetRID Service Provider under test.

**[astm.f3411.v22a.NET0500](../../../../requirements/astm/f3411/v22a.md)** requires a Service Provider to provide a persistently supported test instance of their implementation.
This check will fail if the flight was not successfully injected.

#### Valid flight check

TODO: Validate injected flights, especially to make sure they contain the specified injection IDs

Per **[interuss.automated_testing.rid.injection.UpsertTestResult](../../../../requirements/interuss/automated_testing/rid/injection.md)**, the NetRID Service Provider under test should only make valid modifications to the injected flights.  This includes:
* A flight with the specified injection ID must be returned.

#### 🛑 Identifiable flights check

This particular test requires each flight to be uniquely identifiable by its 2D telemetry position; the same (lat, lng) pair may not appear in two different telemetry points, even if the two points are in different injected flights.  This should generally be achieved by injecting appropriate data.

### Service Provider polling test step

If a DSS was provided to this test scenario, uss_qualifier acts as a Display Provider to query Service Providers under test in this step.

#### ⚠️ ISA query check

**[interuss.f3411.dss_endpoints.SearchISAs](../../../../requirements/interuss/f3411/dss_endpoints.md)** requires a USS providing a DSS instance to implement the DSS endpoints of the OpenAPI specification.  If uss_qualifier is unable to query the DSS for ISAs, this check will fail.

#### ⚠️ Area too large check

**[astm.f3411.v22a.NET0250](../../../../requirements/astm/f3411/v22a.md)** requires that a NetRID Service Provider rejects a request for a very large view area with a diagonal greater than *NetMaxDisplayAreaDiagonal*.  If such a large view is requested and a 413 error code is not received, then this check will fail.

#### [Flight presence checks](./display_data_evaluator_flight_presence.md)

#### ⚠️ Flights data format check

**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** and **[astm.f3411.v22a.NET0340](../../../../requirements/astm/f3411/v22a.md)** requires a Service Provider to implement the P2P portion of the OpenAPI specification. This check will fail if the response to the /flights endpoint does not validate against the OpenAPI-specified schema.

#### [Flight consistency with Common Data Dictionary checks](./common_dictionary_evaluator_sp_flight.md)

#### ⚠️ Recent positions timestamps check

**[astm.f3411.v22a.NET0270](../../../../requirements/astm/f3411/v22a.md)** requires all recent positions to be within the NetMaxNearRealTimeDataPeriod. This check will fail if any of the reported positions are older than the maximally allowed period plus NetSpDataResponseTime99thPercentile.

#### ⚠️ Recent positions for aircraft crossing the requested area boundary show only one position before or after crossing check

**[astm.f3411.v22a.NET0270](../../../../requirements/astm/f3411/v22a.md)** requires that when an aircraft enters or leaves the queried area, the last or first reported position outside the area is provided in the recent positions, as long as it is not older than NetMaxNearRealTimeDataPeriod.

This implies that any recent position outside the area must be either preceded or followed by a position inside the area.

(This check validates NET0270 b and c).

#### ⚠️ Successful flight details query check

**[astm.f3411.v22a.NET0710,2](../../../../requirements/astm/f3411/v22a.md)** and **[astm.f3411.v22a.NET0340](../../../../requirements/astm/f3411/v22a.md) require a Service Provider to implement the GET flight details endpoint.  This check will fail if uss_qualifier cannot query that endpoint (specified in the ISA present in the DSS) successfully.

#### ⚠️ Flight details data format check

**[astm.f3411.v22a.NET0710,2](../../../../requirements/astm/f3411/v22a.md)** and **[astm.f3411.v22a.NET0340](../../../../requirements/astm/f3411/v22a.md) require a Service Provider to implement the P2P portion of the OpenAPI specification.  This check will fail if the response to the flight details endpoint does not validate against the OpenAPI-specified schema.

#### [Flight details consistency with Common Data Dictionary checks](./common_dictionary_evaluator_sp_flight_details.md)

### Observer polling test step

In this step, all observers are queried for the flights they observe.  Based on the known flights that were injected into the SPs in the first step, these observations are checked against expected behavior/data.  Observation rectangles are chosen to encompass the known flights when possible.

#### ⚠️ Area too large check

**[astm.f3411.v22a.NET0430](../../../../requirements/astm/f3411/v22a.md)** require that a NetRID Display Provider reject a request for a very large view area with a diagonal greater than *NetMaxDisplayAreaDiagonal*.  If such a large view is requested and a 413 error code is not received, then this check will fail.

#### ⚠️ Successful observation check

Per **[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)**, the call to each observer is expected to succeed since a valid view was provided by uss_qualifier.

#### [Clustering checks](./display_data_evaluator_clustering.md)

#### ⚠️ Duplicate flights check

Per **[interuss.automated_testing.rid.observation.UniqueFlights](../../../../requirements/interuss/automated_testing/rid/observation.md)**, the same flight ID may not be reported by a Display Provider for two flights in the same observation.

#### [Flight presence checks](./display_data_evaluator_flight_presence.md)

#### [Flight consistency with Common Data Dictionary checks](./common_dictionary_evaluator_dp_flight.md)

#### ⚠️ Telemetry being used when present check

**[astm.f3411.v22a.NET0290](../../../../requirements/astm/f3411/v22a.md)** requires a SP uses Telemetry vs extrapolation when telemetry is present.

#### ⚠️ Successful details observation check

Per **[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)**, the call for flight details is expected to succeed since a valid ID was provided by uss_qualifier.

#### [Flight details consistency with Common Data Dictionary checks](./common_dictionary_evaluator_dp_flight_details.md)

### Validate Mock USS received notification test step

This test step verifies that the mock_uss for which a subscription was registered before flight injection properly received a notification from each Service Provider
at which a flight was injected.

#### ⚠️ Service Provider issued a notification check

This check validates that each Service Provider at which a test flight was injected properly notified the mock_uss.

If this is not the case, the respective Service Provider fails to meet **[astm.f3411.v22a.NET0740](../../../../requirements/astm/f3411/v22a.md)**.

#### ⚠️ Service Provider notification was received within delay check

This check validates that the notification from each Service Provider was received by the mock_uss within the specified delay.

**[astm.f3411.v22a.NET0740](../../../../requirements/astm/f3411/v22a.md)** states that a Service Provider must notify the owner of a subscription within `NetDpDataResponse95thPercentile` (1 second) second 95% of the time and `NetDpDataResponse99thPercentile` (3 seconds) 99% of the time as soon as the SP becomes aware of the subscription.

This check will be failed if it takes longer than 3 seconds between the injection of the flight and the notification being received by the mock_uss.

## Cleanup

The cleanup phase of this test scenario attempts to remove injected data from all SPs.

### ⚠️ Successful test deletion check

**[interuss.automated_testing.rid.injection.DeleteTestSuccess](../../../../requirements/interuss/automated_testing/rid/injection.md)**

### [Clean Subscriptions](./dss/test_steps/clean_workspace.md)

Remove all created subscriptions from the DSS.
