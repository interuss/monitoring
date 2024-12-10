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

### evaluation_configuration

This [`EvaluationConfigurationResource`](../../../../resources/netrid/evaluation.py) defines how to gauge success when observing the injected flights.

### dss_pool

If specified, uss_qualifier will act as a Display Provider and check a DSS instance from this [`DSSInstanceResource`](../../../../resources/astm/f3411/dss.py) for appropriate identification service areas and then query the corresponding USSs with flights using the same session.

## Nominal flight test case

### Injection test step

In this step, uss_qualifier injects a single nominal flight into each SP under test, usually with a start time in the future.  Each SP is expected to queue the provided telemetry and later simulate that telemetry coming from an aircraft at the designated timestamps.

#### Successful injection check

Per **[interuss.automated_testing.rid.injection.UpsertTestSuccess](../../../../requirements/interuss/automated_testing/rid/injection.md)**, the injection attempt of the valid flight should succeed for every NetRID Service Provider under test.

**[astm.f3411.v22a.NET0500](../../../../requirements/astm/f3411/v22a.md)** requires a Service Provider to provide a persistently supported test instance of their implementation.
This check will fail if the flight was not successfully injected.

#### Valid flight check

TODO: Validate injected flights, especially to make sure they contain the specified injection IDs

Per **[interuss.automated_testing.rid.injection.UpsertTestResult](../../../../requirements/interuss/automated_testing/rid/injection.md)**, the NetRID Service Provider under test should only make valid modifications to the injected flights.  This includes:
* A flight with the specified injection ID must be returned.

#### Identifiable flights check

This particular test requires each flight to be uniquely identifiable by its 2D telemetry position; the same (lat, lng) pair may not appear in two different telemetry points, even if the two points are in different injected flights.  This should generally be achieved by injecting appropriate data.

### Service Provider polling test step

If a DSS was provided to this test scenario, uss_qualifier acts as a Display Provider to query Service Providers under test in this step.

#### ISA query check

**[interuss.f3411.dss_endpoints.SearchISAs](../../../../requirements/interuss/f3411/dss_endpoints.md)** requires a USS providing a DSS instance to implement the DSS endpoints of the OpenAPI specification.  If uss_qualifier is unable to query the DSS for ISAs, this check will fail.

#### Area too large check

**[astm.f3411.v22a.NET0250](../../../../requirements/astm/f3411/v22a.md)** requires that a NetRID Service Provider rejects a request for a very large view area with a diagonal greater than *NetMaxDisplayAreaDiagonal*.  If such a large view is requested and a 413 error code is not received, then this check will fail.

#### Premature flight check

The timestamps of the injected telemetry usually start in the future.  If a flight with injected telemetry only in the future is observed prior to the timestamp of the first telemetry point, this check will fail because the SP does not satisfy **[interuss.automated_testing.rid.injection.ExpectedBehavior](../../../../requirements/interuss/automated_testing/rid/injection.md)**.

#### Missing flight check

**[astm.f3411.v22a.NET0610](../../../../requirements/astm/f3411/v22a.md)** requires that SPs make all UAS operations discoverable over the duration of the flight plus *NetMaxNearRealTimeDataPeriod*, so each injected flight should be observable during this time.  If a flight is not observed during its appropriate time period, this check will fail.

**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** and **[astm.f3411.v22a.NET0340](../../../../requirements/astm/f3411/v22a.md) require a Service Provider to implement the GET flights endpoint.  This check will also fail if uss_qualifier cannot query that endpoint (specified in the ISA present in the DSS) successfully.

The identity of flights is determined by precisely matching the known injected positions.  If the flight can be found, the USS may not have met **[astm.f3411.v22a.NET0260,Table1,10](../../../../requirements/astm/f3411/v22a.md)** or **[astm.f3411.v22a.NET0260,Table1,11](../../../../requirements/astm/f3411/v22a.md)** prescribing provision of position data consistent with the common data dictionary.

#### Lingering flight check

**[astm.f3411.v22a.NET0270](../../../../requirements/astm/f3411/v22a.md)** requires a SP to provide flights up to *NetMaxNearRealTimeDataPeriod* in the past, but an SP should preserve privacy and ensure relevancy by not sharing flights that are further in the past than this window.

#### Flights data format check

**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** and **[astm.f3411.v22a.NET0340](../../../../requirements/astm/f3411/v22a.md)** requires a Service Provider to implement the P2P portion of the OpenAPI specification. This check will fail if the response to the /flights endpoint does not validate against the OpenAPI-specified schema.

#### [Flight consistency with Common Data Dictionary checks](./common_dictionary_evaluator_sp_flight.md)

#### Recent positions timestamps check
**[astm.f3411.v22a.NET0270](../../../../requirements/astm/f3411/v22a.md)** requires all recent positions to be within the NetMaxNearRealTimeDataPeriod. This check will fail if any of the reported positions are older than the maximally allowed period plus NetSpDataResponseTime99thPercentile.

#### Recent positions for aircraft crossing the requested area boundary show only one position before or after crossing check
**[astm.f3411.v22a.NET0270](../../../../requirements/astm/f3411/v22a.md)** requires that when an aircraft enters or leaves the queried area, the last or first reported position outside the area is provided in the recent positions, as long as it is not older than NetMaxNearRealTimeDataPeriod.

This implies that any recent position outside the area must be either preceded or followed by a position inside the area.

(This check validates NET0270 b and c).

#### Successful flight details query check

**[astm.f3411.v22a.NET0710,2](../../../../requirements/astm/f3411/v22a.md)** and **[astm.f3411.v22a.NET0340](../../../../requirements/astm/f3411/v22a.md) require a Service Provider to implement the GET flight details endpoint.  This check will fail if uss_qualifier cannot query that endpoint (specified in the ISA present in the DSS) successfully.

#### Flight details data format check

**[astm.f3411.v22a.NET0710,2](../../../../requirements/astm/f3411/v22a.md)** and **[astm.f3411.v22a.NET0340](../../../../requirements/astm/f3411/v22a.md) require a Service Provider to implement the P2P portion of the OpenAPI specification.  This check will fail if the response to the flight details endpoint does not validate against the OpenAPI-specified schema.

#### [Flight details consistency with Common Data Dictionary checks](./common_dictionary_evaluator_sp_flight_details.md)

### Observer polling test step

In this step, all observers are queried for the flights they observe.  Based on the known flights that were injected into the SPs in the first step, these observations are checked against expected behavior/data.  Observation rectangles are chosen to encompass the known flights when possible.

#### Area too large check

**[astm.f3411.v22a.NET0430](../../../../requirements/astm/f3411/v22a.md)** require that a NetRID Display Provider reject a request for a very large view area with a diagonal greater than *NetMaxDisplayAreaDiagonal*.  If such a large view is requested and a 413 error code is not received, then this check will fail.

#### Successful observation check

Per **[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)**, the call to each observer is expected to succeed since a valid view was provided by uss_qualifier.

#### [Clustering checks](./display_data_evaluator_clustering.md)

#### Duplicate flights check

Per **[interuss.automated_testing.rid.observation.UniqueFlights](../../../../requirements/interuss/automated_testing/rid/observation.md)**, the same flight ID may not be reported by a Display Provider for two flights in the same observation.

#### Premature flight check

The timestamps of the injected telemetry usually start in the future.  If a flight with injected telemetry only in the future is observed prior to the timestamp of the first telemetry point, this check will fail because the SP does not satisfy **[interuss.automated_testing.rid.injection.ExpectedBehavior](../../../../requirements/interuss/automated_testing/rid/injection.md)**.

#### Missing flight check

**[astm.f3411.v22a.NET0610](../../../../requirements/astm/f3411/v22a.md)** require that SPs make all UAS operations discoverable over the duration of the flight plus *NetMaxNearRealTimeDataPeriod*, so each injected flight should be observable during this time.  If one of the flights is not observed during its appropriate time period, this check will fail.

#### Lingering flight check

NET0260 requires a SP to provide flights up to *NetMaxNearRealTimeDataPeriod* in the past, but an SP should preserve privacy and ensure relevancy by not sharing flights that are further in the past than this window.

#### [Flight consistency with Common Data Dictionary checks](./common_dictionary_evaluator_dp_flight.md)

#### Telemetry being used when present check

**[astm.f3411.v22a.NET0290](../../../../requirements/astm/f3411/v22a.md)** requires a SP uses Telemetry vs extrapolation when telemetry is present.

#### Successful details observation check

Per **[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)**, the call for flight details is expected to succeed since a valid ID was provided by uss_qualifier.

#### [Flight details consistency with Common Data Dictionary checks](./common_dictionary_evaluator_dp_flight_details.md)

## Cleanup

The cleanup phase of this test scenario attempts to remove injected data from all SPs.

### Successful test deletion check

**[interuss.automated_testing.rid.injection.DeleteTestSuccess](../../../../requirements/interuss/automated_testing/rid/injection.md)**
