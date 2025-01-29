# ASTM NetRID Display Provider behavior test scenario

## Overview

This scenario attempts to cause a Display Provider to issue queries to a Service Provider for a too large area.

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

### [Create ISA test step](./dss/test_steps/put_isa.md)

Create an ISA in the area specified by the `isa` resource, valid from the moment the scenario runs and for a duration of 5 minutes.

The USS base URL will be the one specified by the passed `mock_uss` resource.

#### 🛑 Create an ISA check

If the ISA cannot be created, the PUT DSS endpoint in **[astm.f3411.v22a.DSS0030,a](../../../../requirements/astm/f3411/v22a.md)** is likely not implemented correctly.

## Display Provider Behavior test case

### Query acceptable diagonal area test step

This test step queries the Display Provider for the exact area of the ISA.

#### 🛑 Observation query succeeds check

**[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)** requires that the Display Provider provides data for queries for an area with a diagonal no greater than `NetMaxDisplayAreaDiagonal` (7km).

### Query maximum diagonal area test step

#### 🛑 Maximum diagonal area query succeeds check

**[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)** requires that the Display Provider provides data for queries for an area with a diagonal no greater than `NetMaxDisplayAreaDiagonal` (7km).

If the Display Provider does not respond to a request for data in an area with a diagonal of `NetMaxDisplayAreaDiagonal`, it is in violation of this requirement.

### Query too long diagonal test step

#### 🛑 Too long diagonal query fails check

**[astm.f3411.v22a.NET0430](../../../../requirements/astm/f3411/v22a.md)** requires that the Display Provider provides data for queries for an area with a diagonal no greater than `NetMaxDisplayAreaDiagonal` (7km).

If the Display Provider responds with anything else than an error, it is in violation of this requirement.

### [Verify query to SP test step](../../../interuss/mock_uss/get_mock_uss_interactions.md)

Validate that the Display Provider queried the SP and behaved correctly while doing so.

#### 🛑 DP queried SP check

**[astm.f3411.v22a.NET0240](../../../../requirements/astm/f3411/v22a.md)** requires that a Display Provider queries a Service Provider for areas with a diagonal no greater than `NetMaxDisplayAreaDiagonal` (7km).

If the Display Provider failed to issue requests when it was queried for valid areas, it is in violation of this requirement.

#### 🛑 No query to SP exceeded the maximum diagonal check

**[astm.f3411.v22a.NET0240](../../../../requirements/astm/f3411/v22a.md)** requires that a Display Provider queries a Service Provider for areas with a diagonal no greater than `NetMaxDisplayAreaDiagonal` (7km).

If the Display Provider has issued such requests, it is in violation of this requirement.

## Cleanup

The cleanup phase of this test scenario attempts to remove injected data from all SPs.

### [Clean ISA](./dss/test_steps/clean_workspace.md)

Remove the created ISA from the DSS.
