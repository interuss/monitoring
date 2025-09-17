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

#### ⚠️ Operational intent details requests take no more than [MaxRespondToOIDetailsRequest] second 95% of the time check

If the 95th percentile of the requests durations is higher than the threshold `MaxRespondToOIDetailsRequest` (1 second),
this check will fail per **[astm.f3548.v21.SCD0075](../../../requirements/astm/f3548/v21.md)**.

## Interoperability test instance is available test case

### Interoperability test instance is available test step

This step verifies that interactions with the interoperability test instances happened and where at least partly successful.

#### ⚠️ Interoperability test instance is available check

This check ensures that interactions with the interoperability test instance that each USS must provide are possible.

If all interactions fail, or if no test instance can be reached, the USS is failing to meet **[astm.f3548.v21.GEN0300](../../../requirements/astm/f3548/v21.md)**.

If no interaction with a test instance was found, this check is skipped.

## Notifications to operator test case

When certain circumstances occur, USSs must notify UAS personnel or the operator's automation system within a fixed amount of time a certain fraction of time.  This test case examines notification latency across all tests performed during this test run.

### Notifications for causing conflicts test step

#### ⚠️ Notifications for causing conflicts check

If 95% of the USS's notifications regarding conflicts caused by the operator's flight do not appear in the USS's list of user notifications within `ConflictingOIMaxUserNotificationTime` (5 seconds) of completing the planning operation, this check will fail per **[astm.f3548.v21.SCD0090](../../../requirements/astm/f3548/v21.md)**.

To find the notifications considered, review the reports for "Nominal planning: conflict with higher priority" scenarios.

### Notifications for observing conflicts test step

#### ⚠️ Notifications for observing conflicts check

If 95% of the USS's notifications regarding conflicts affecting the operator's flight do not appear in the USS's list of user notifications within `ConflictingOIMaxUserNotificationTime` (5 seconds) of completing the planning operation, this check will fail per **[astm.f3548.v21.SCD0095](../../../requirements/astm/f3548/v21.md)**.

To find the notifications considered, review the reports for "Nominal planning: conflict with higher priority" scenarios.
