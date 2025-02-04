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

### [Injection test step](./fragments/flight_injection.md)

### [Service Provider polling test step](./fragments/sp_polling.md)

If a DSS was provided to this test scenario, uss_qualifier acts as a Display Provider to query Service Providers under test in this step.

#### [Validate injected flight](./fragments/flight_check.md)

#### [Validate injected flight details](./fragments/flight_details_check.md)

#### ⚠️ Area too large check

**[astm.f3411.v22a.NET0250](../../../../requirements/astm/f3411/v22a.md)** requires that a NetRID Service Provider rejects a request for a very large view area with a diagonal greater than *NetMaxDisplayAreaDiagonal*.  If such a large view is requested and a 413 error code is not received, then this check will fail.

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

## Cleanup

The cleanup phase of this test scenario attempts to remove injected data from all SPs.

### ⚠️ Successful test deletion check

**[interuss.automated_testing.rid.injection.DeleteTestSuccess](../../../../requirements/interuss/automated_testing/rid/injection.md)**
