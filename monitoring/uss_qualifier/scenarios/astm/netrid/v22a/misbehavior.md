# ASTM NetRID SP clients misbehavior handling test scenario

## Overview

In this scenario, the service provider's endpoint are accessed directly with missing or incorrect credentials. Resources that exists as well as resources that are not expected to exist are queried.

## Resources

### flights_data

A [`FlightDataResource`](../../../../resources/netrid/flight_data.py) containing 1 nominal flight per SP under test.

### service_providers

A set of [`NetRIDServiceProviders`](../../../../resources/netrid/service_providers.py) to be tested for proper request authentication. This scenario requires at least one SP under test.

### evaluation_configuration

This [`EvaluationConfigurationResource`](../../../../resources/netrid/evaluation.py) defines how to gauge success when observing the injected flights.

### dss_pool

A [`DSSInstanceResource`](../../../../resources/astm/f3411/dss.py) is required for providing the qualifier with the flights URL of the service providers being tested.

## Unauthenticated requests test case

### Injection test step

In this step, uss_qualifier injects a single nominal flight into each SP under test, usually with a start time in the future.  Each SP is expected to queue the provided telemetry and later simulate that telemetry coming from an aircraft at the designated timestamps.

#### Successful injection check

Per **[interuss.automated_testing.rid.injection.UpsertTestSuccess](../../../../requirements/interuss/automated_testing/rid/injection.md)**, the injection attempt of the valid flight should succeed for every NetRID Service Provider under test.

**[astm.f3411.v22a.NET0500](../../../../requirements/astm/f3411/v22a.md)** requires a Service Provider to provide a persistently supported test instance of their implementation.
This check will fail if the flight was not successfully injected.

#### Identifiable flights check

This particular test requires each flight to be uniquely identifiable by its 2D telemetry position; the same (lat, lng) pair may not appear in two different telemetry points, even if the two points are in different injected flights.  This should generally be achieved by injecting appropriate data.

### Unauthenticated requests test step

In order to properly test whether the SP handles authentication correctly, this step will first attempt to do a request with the proper credentials
to confirm that the requested data is indeed available to any authorized query.

It then repeats the exact same request with incorrect credentials, and expects this to fail.

#### Missing credentials check

This check ensures that all requests are properly authenticated, as required by **[astm.f3411.v22a.NET0210](../../../../requirements/astm/f3411/v22a.md)**,
and that requests for existing flights that are executed with missing or incorrect credentials fail.

## Cleanup

The cleanup phase of this test scenario attempts to remove injected data from all SPs.

### Successful test deletion check

**[interuss.automated_testing.rid.injection.DeleteTestSuccess](../../../../requirements/interuss/automated_testing/rid/injection.md)**
