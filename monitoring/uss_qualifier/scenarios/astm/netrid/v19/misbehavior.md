# ASTM NetRID SP clients misbehavior handling test scenario

## Overview

In this scenario, the service provider's endpoints are accessed directly to test missing credentials as well as invalid requests. Resources that exists as well as resources that are not expected to exist are queried.

## Resources

### flights_data

A [`FlightDataResource`](../../../../resources/netrid/flight_data.py) containing 1 nominal flight per SP under test.

### service_providers

A set of [`NetRIDServiceProviders`](../../../../resources/netrid/service_providers.py) to be tested for proper request authentication. This scenario requires at least one SP under test.

### evaluation_configuration

This [`EvaluationConfigurationResource`](../../../../resources/netrid/evaluation.py) defines how to gauge success when observing the injected flights.

### dss_pool

A [`DSSInstanceResource`](../../../../resources/astm/f3411/dss.py) is required for providing the qualifier with the flights URL of the service providers being tested.

## Invalid requests test case

### [Injection test step](./fragments/flight_injection.md)

### Invalid search area test step

This step will attempt to search for flights in a rectangular area with a diagonal greater than [NetMaxDisplayAreaDiagonal] km. First, the Service Providers with service in the large area will be determined from the DSS and then each Service Provider will be queried for flights (this should succeed). Then each Service Provider will be queried again for flights, this time using an unacceptably-large area (this should fail).

#### [Service provider queries test step](../v19/fragments/sp_simple_queries.md)

#### ⚠️ Area too large check

**[astm.f3411.v19.NET0250](../../../../requirements/astm/f3411/v19.md)** requires that a NetRID Service Provider rejects a request for a very large view area with a diagonal greater than *NetMaxDisplayAreaDiagonal*.  If such a large view is requested and a 400 or 413 error code is not received or the response contains Remote ID data, then this check will fail.

### Unauthenticated requests test step

in order to properly test whether the SP handles authentication correctly, after identifying the SP contact information via its ISA in the DSS, this step will first attempt to do a flights request with the proper credentials to confirm that the requested data is indeed available to any authorized query.

It then repeats the exact same request without credentials, and expects this to fail.

#### [Service provider queries test step](../v19/fragments/sp_simple_queries.md)

#### ⚠️ Missing credentials check

This check ensures that all requests are properly authenticated, as required by **[astm.f3411.v19.NET0210](../../../../requirements/astm/f3411/v19.md)**,
and that requests for existing flights that are executed with missing credentials fail.

### Incorrectly authenticated requests test step

This step is similar to unauthenticated requests, but uses incorrectly-authenticated requests instead.

#### [Service provider queries test step](../v19/fragments/sp_simple_queries.md)

#### ⚠️ Invalid credentials check
This check ensures that all requests are properly authenticated, as required by **[astm.f3411.v19.NET0210](../../../../requirements/astm/f3411/v19.md)**,
and that requests for existing flights that are executed with incorrect credentials fail.

## Cleanup

The cleanup phase of this test scenario attempts to remove injected data from all SPs.

### ⚠️ Successful test deletion check

**[interuss.automated_testing.rid.injection.DeleteTestSuccess](../../../../requirements/interuss/automated_testing/rid/injection.md)**
