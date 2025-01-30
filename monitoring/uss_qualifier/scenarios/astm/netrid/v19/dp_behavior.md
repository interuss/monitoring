# ASTM NetRID Display Provider behavior test scenario

## Overview

This scenario observes Display Provider behavior when interacting with a Service Provider.  It attempts to observe the Display Provider correctly acknowledging an ISA notification from the Service Provider, and it also attempts to cause a Display Provider to issue invalid queries to the Service Provider.

## Resources

### observers

The set of [`NetRIDObserversResource`](../../../../resources/netrid/observers.py) that will be tested by this scenario.

### mock_uss

[`MockUSSResource`](../../../../resources/interuss/mock_uss/client.py) that will play the role of the service provider being queried by the display provider under test.

### id_generator

[`IDGeneratorResource`](../../../../resources/interuss/id_generator.py) providing the ISA ID for this scenario.

### dss_pool

[`DSSInstanceResource`](../../../../resources/astm/f3411/dss.py) which will be used to create the ISA that will cause the display provider to call the mock_uss.

### isa

[`ServiceAreaResource`](../../../../resources/netrid/service_area.py) defining the area for which an ISA will be created and around which the queries to the display provider under test will be built.

## Setup test case

### [Clean workspace test step](./dss/test_steps/clean_workspace.md)

## Subscription priming test case

Observers are queried for flights in an attempt to cause the Display Providers to establish subscriptions so that mock_uss will send ISA notifications when it creates its ISA.

### Query observers test step

Each observer is queried for flights in the empty area.

#### 🛑 Observation query succeeds check

**[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)** requires that the Display Provider provides observation data for valid queries.

## Create flight test case

This test step has the mock_uss begin a new flight by establishing an ISA.

### [Create ISA test step](./dss/test_steps/put_isa.md)

uss_qualifier, acting as mock_uss, creates an ISA in the area specified by the `isa` resource, valid from the moment the scenario runs and for a duration of 5 minutes.

The USS base URL will be the one specified by the passed `mock_uss` resource.

#### 🛑 Create an ISA check

If the ISA cannot be created, the PUT DSS endpoint in **[astm.f3411.v19.DSS0030,a](../../../../requirements/astm/f3411/v19.md)** is likely not implemented correctly.

#### ⚠️ DP accepted ISA notification check

Prior to ISA creation, the Display Providers of one or more observers may have established subscriptions for the area due to subscription priming above.  If a subscription was present but the managing Display Provider did not acknowledge a notification correctly, the Display Provider will have failed to meet **[astm.f3411.v19.NET0730](../../../../requirements/astm/f3411/v19.md)**.  If a Display Provider did not establish a subscription, this check cannot be evaluated as no notification was sent.

TODO: Implement this check

## Display Provider Behavior test case

### Query acceptable diagonal area test step

This test step queries the Display Provider for the exact area of the ISA.

#### 🛑 Observation query succeeds check

**[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)** requires that the Display Provider provides data for queries for an area with a diagonal no greater than `NetMaxDisplayAreaDiagonal` (3,6).

### Query maximum diagonal area test step

#### ⚠️ Maximum diagonal area query succeeds check

**[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)** requires that the Display Provider provides data for queries for an area with a diagonal no greater than `NetMaxDisplayAreaDiagonal` (3,6).

If the Display Provider does not respond to a request for data in an area with a diagonal of `NetMaxDisplayAreaDiagonal`, it is in violation of this requirement.

### Query too long diagonal test step

#### ⚠️ Too long diagonal query fails check

**[astm.f3411.v19.NET0430](../../../../requirements/astm/f3411/v19.md)** requires that the Display Provider provides data for queries for an area with a diagonal no greater than `NetMaxDisplayAreaDiagonal` (3,6).

If the Display Provider responds with anything else than an error, it is in violation of this requirement.

### Verify query to SP test step

Validate that the Display Provider queried the SP and behaved correctly while doing so.

#### [Get mock_uss interactions](../../../interuss/mock_uss/get_mock_uss_interactions.md)

#### 🛑 DP queried SP check

**[astm.f3411.v19.NET0240](../../../../requirements/astm/f3411/v19.md)** requires that a Display Provider queries a Service Provider for areas with a diagonal no greater than `NetMaxDisplayAreaDiagonal` (3,6).

If the Display Provider failed to issue requests when it was queried for valid areas, it is in violation of this requirement.

#### 🛑 No query to SP exceeded the maximum diagonal check

**[astm.f3411.v19.NET0240](../../../../requirements/astm/f3411/v19.md)** requires that a Display Provider queries a Service Provider for areas with a diagonal no greater than `NetMaxDisplayAreaDiagonal` (3,6).

If the Display Provider has issued such requests, it is in violation of this requirement.

## Cleanup

The cleanup phase of this test scenario attempts to remove injected data from all SPs.

### [Clean ISA](./dss/test_steps/clean_workspace.md)

Remove the created ISA from the DSS.
