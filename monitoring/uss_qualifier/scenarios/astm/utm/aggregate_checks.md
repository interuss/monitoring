# ASTM F3548 UTM aggregate checks test scenario

## Overview
In this special scenario, the report of previously executed ASTM F3548 UTM scenario(s) are evaluated for the
performances of the queries made during their execution.

## Resources

### flight_planners
The flight planners subject to evaluation.

## Performance of SCD requests to USS test case

### Performance of successful operational intent details requests test step

In this step, all successful requests for operational intent details made to the USSs that are part of the flight
planners provided as resource are used to determine and evaluate the 95th percentile of the requests durations.

#### Operational intent details requests take no more than [MaxRespondToOIDetailsRequest] second 95% of the time check

If the 95th percentile of the requests durations is higher than the threshold `MaxRespondToOIDetailsRequest` (1 second),
this check will fail per **[astm.f3548.v21.SCD0075](../../../requirements/astm/f3548/v21.md)**.
