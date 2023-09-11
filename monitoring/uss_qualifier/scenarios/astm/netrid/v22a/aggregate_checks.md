# ASTM F3411-22a NetRID aggregate checks test scenario

## Overview
In this special scenario, the report of previously executed ASTM F3411-22a NetRID scenario(s) are evaluated for the
performances of the queries made during their execution.

## Resources

### report_resource
The report to evaluate. This resource is automatically injected by the test framework.

### service_providers
The service providers to evaluate in the report.

### observers
The observers to evaluate in the report.

## Performance of Display Providers requests test case

### Performance of /display_data requests test step
In this step, all successful display data queries made during the execution of the previous scenarios are aggregated per
observer and per request (identified by their URLs). For each of those, and using the session length
`NetMinSessionLength`, the queries are split between initial and subsequent ones.
The percentiles of both all the initial and all the subsequent queries are then computed to be checked.

#### Performance of /display_data initial requests check
**[astm.f3411.v22a.NET0420](../../../../requirements/astm/f3411/v22a.md)** requires that the 95th and 99th percentiles
of the durations for the initial display data queries do not exceed the respectives thresholds
`NetDpInitResponse95thPercentile` and `NetDpInitResponse99thPercentile`.

#### Performance of /display_data subsequent requests check
**[astm.f3411.v22a.NET0440](../../../../requirements/astm/f3411/v22a.md)** requires that the 95th and 99th percentiles
of the durations for the subsequent display data queries do not exceed the respectives thresholds
`NetDpDataResponse95thPercentile` and `NetDpDataResponse99thPercentile`.

## Performance of Service Providers requests test case

### Performance of /flights?view requests test step

#### Performance for replies to requested flights in an area check

**[astm.f3411.v22a.NET0260-a](../../../../requirements/astm/f3411/v22a.md)** requires that the 95th and 99th percentiles
of the durations for the replies to requested flights in an area do not exceed the respective thresholds
`NetSpDataResponseTime95thPercentile` (1 second) and `NetSpDataResponseTime99thPercentile` (3 seconds).

## Mock USS interactions evaluation test case

In this test case, the interactions with a mock_uss instance (if provided) are obtained and then examined to verify
compliance with requirements.

### Get mock USS interactions test step

### Evaluate mock USS interactions test step

#### No large Display Provider queries check

If one of the Display Provider test participants was found to have sent a query to mock_uss with a larger-than-allowed
area requested, then that participant will have violated **[astm.f3411.v22a.NET0240](../../../../requirements/astm/f3411/v22a.md)**.

TODO: Implement this check
