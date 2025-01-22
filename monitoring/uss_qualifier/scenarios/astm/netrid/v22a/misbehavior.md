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

### [Injection test step](./fragments/flight_injection.md)

### Unauthenticated requests test step

In order to properly test whether the SP handles authentication correctly, this step will first attempt to do a request with the proper credentials
to confirm that the requested data is indeed available to any authorized query.

It then repeats the exact same request without credentials, and expects this to fail.

#### Missing credentials check

This check ensures that all requests are properly authenticated, as required by **[astm.f3411.v22a.NET0210](../../../../requirements/astm/f3411/v22a.md)**,
and that requests for existing flights that are executed with missing credentials fail.

### Incorrectly authenticated requests test step

This step is similar to unauthenticated requests, but uses incorrectly-authenticated requests instead.

#### ⚠️ Invalid credentials check

This check ensures that all requests are properly authenticated, as required by **[astm.f3411.v22a.NET0210](../../../../requirements/astm/f3411/v22a.md)**,
and that requests for existing flights that are executed with incorrect credentials fail.

## Cleanup

The cleanup phase of this test scenario attempts to remove injected data from all SPs.

### Successful test deletion check

**[interuss.automated_testing.rid.injection.DeleteTestSuccess](../../../../requirements/interuss/automated_testing/rid/injection.md)**
