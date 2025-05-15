# ASTM NetRID networked UAS disconnection test scenario

## Overview

In this scenario, a single nominal flight simulating a disconnection is injected into each NetRID Service Provider (SP) under test.  Each of the injected flights is expected to be visible to the uss_qualifier, which will check that every SP behaves correctly when a flight disconnects.

Note that disconnections are simulated by not injecting any telemetry anymore. As such, within the test framework, a disconnected flight cannot be distinguished from a flight that ended normally.

This scenario evaluates that SPs correctly behave once they stop receiving telemetry for a flight.

## Resources

### flights_data

A [`FlightDataResource`](../../../../resources/netrid/flight_data.py) containing 1 nominal flight per SP under test.

### service_providers

A set of [`NetRIDServiceProviders`](../../../../resources/netrid/service_providers.py) to be tested via the injection of RID flight data.  This scenario requires at least one SP under test.

### evaluation_configuration

This [`EvaluationConfigurationResource`](../../../../resources/netrid/evaluation.py) defines how to gauge success when observing the injected flights.

### dss_pool

uss_qualifier acts as a Display Provider querying the Service Provider(s) under test. As such, it will query an instance from the provided [`DSSInstanceResource`](../../../../resources/astm/f3411/dss.py) to obtain the relevant identification service areas and then query the corresponding USSs.

## Networked UAS disconnect test case

### Injection test step

In this step, uss_qualifier injects a single nominal flight into each SP under test, usually with a start time in the future.  Each SP is expected to queue the provided telemetry and later simulate that telemetry coming from an aircraft at the designated timestamps.

#### 🛑 Successful injection check

Per **[interuss.automated_testing.rid.injection.UpsertTestSuccess](../../../../requirements/interuss/automated_testing/rid/injection.md)**, the injection attempt of the valid flight should succeed for every NetRID Service Provider under test.

**[astm.f3411.v19.NET0500](../../../../requirements/astm/f3411/v19.md)** requires a Service Provider to provide a persistently supported test instance of their implementation.
This check will fail if the flight was not successfully injected.

#### 🛑 Valid flight check

TODO: Validate injected flights, especially to make sure they contain the specified injection IDs

Per **[interuss.automated_testing.rid.injection.UpsertTestResult](../../../../requirements/interuss/automated_testing/rid/injection.md)**, the NetRID Service Provider under test should only make valid modifications to the injected flights.  This includes:
* A flight with the specified injection ID must be returned.

#### 🛑 Identifiable flights check

This particular test requires each flight to be uniquely identifiable by its 2D telemetry position; the same (lat, lng) pair may not appear in two different telemetry points, even if the two points are in different injected flights.  This should generally be achieved by injecting appropriate data.

### Service Provider polling test step

uss_qualifier acts as a Display Provider to query Service Providers under test in this step.

#### ⚠️ ISA query check

**[interuss.f3411.dss_endpoints.SearchISAs](../../../../requirements/interuss/f3411/dss_endpoints.md)** requires a USS providing a DSS instance to implement the DSS endpoints of the OpenAPI specification.  If uss_qualifier is unable to query the DSS for ISAs, this check will fail.

#### [Flight presence checks](./display_data_evaluator_flight_presence.md)

#### ⚠️ Flights data format check

**[astm.f3411.v19.NET0710,1](../../../../requirements/astm/f3411/v19.md)** and **[astm.f3411.v19.NET0340](../../../../requirements/astm/f3411/v19.md)** requires a Service Provider to implement the P2P portion of the OpenAPI specification. This check will fail if the response to the /flights endpoint does not validate against the OpenAPI-specified schema.

#### [Flight consistency with Common Data Dictionary checks](./common_dictionary_evaluator_sp_flight.md)

#### 🛑 Recent positions timestamps check
**[astm.f3411.v19.NET0270](../../../../requirements/astm/f3411/v19.md)** requires all recent positions to be within the NetMaxNearRealTimeDataPeriod. This check will fail if any of the reported positions are older than the maximally allowed period plus NetSpDataResponseTime99thPercentile.

#### 🛑 Recent positions for aircraft crossing the requested area boundary show only one position before or after crossing check
**[astm.f3411.v19.NET0270](../../../../requirements/astm/f3411/v19.md)** requires that when an aircraft enters or leaves the queried area, the last or first reported position outside the area is provided in the recent positions, as long as it is not older than NetMaxNearRealTimeDataPeriod.

This implies that any recent position outside the area must be either preceded or followed by a position inside the area.

(This check validates NET0270 b and c).

#### ⚠️ Disconnected flight is shown as such check

For a networked UAS that loses connectivity during a flight, its associated Service Provider is required to provide any Display Provider requesting data for the flight with the most recent position with the indication that the UAS is disconnected, as per **[astm.f3411.v19.NET0320](../../../../requirements/astm/f3411/v19.md)**.

Service providers are expected to convey to clients that a flight is not sending any telemetry by providing the last received telemetry, including its timestamp. Clients are expected to deduce that a flight is disconnected when its telemetry is getting stale.

Service providers that return anything else than the last received telemetry during `NetMaxNearRealTimeDataPeriodSeconds` (60) after a flight stops disconnects will fail this check.

#### ⚠️ Successful observation check

Per **[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)**, the call to each observer is expected to succeed since a valid view was provided by uss_qualifier.

#### [Clustering checks](./display_data_evaluator_clustering.md)

#### 🛑 Duplicate flights check

Per **[interuss.automated_testing.rid.observation.UniqueFlights](../../../../requirements/interuss/automated_testing/rid/observation.md)**, the same flight ID may not be reported by a Display Provider for two flights in the same observation.

#### [Flight presence checks](./display_data_evaluator_flight_presence.md)

#### [Flight consistency with Common Data Dictionary checks](./common_dictionary_evaluator_dp_flight.md)

#### 🛑 Telemetry being used when present check

**[astm.f3411.v19.NET0290](../../../../requirements/astm/f3411/v19.md)** requires a SP uses Telemetry vs extrapolation when telemetry is present.

### Verify all disconnected flights have been observed as disconnected test step

#### ⚠️ All injected disconnected flights have been observed as disconnected check

**[astm.f3411.v19.NET0320](../../../../requirements/astm/f3411/v19.md)** requires that a Service Provider continues providing the last received telemetry for a flight that has been disconnected.  This check will fail if any of the injected flights simulating a connectivity loss is not observed as disconnected within the window of `NetMaxNearRealTimeDataPeriodSeconds` (60) after the disconnection occurs.

## Cleanup

The cleanup phase of this test scenario attempts to remove injected data from all SPs.

### ⚠️ Successful test deletion check

**[interuss.automated_testing.rid.injection.DeleteTestSuccess](../../../../requirements/interuss/automated_testing/rid/injection.md)**
