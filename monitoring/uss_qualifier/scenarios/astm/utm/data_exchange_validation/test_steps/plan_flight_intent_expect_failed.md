# Plan flight Expect Failed test step

This page describes the content of a common test case where a valid user flight intent fails in a flight planner, because of invalid data for a nearby flight shared by another USS.  See `plan_flight_intent_expect_failed` in [test_steps.py](invalid_op_test_steps.py).

## Plan should fail check

Flight intent data of a nearby flight shared was invalid, therefore it should have been failed to plan by the USS per **[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../../../requirements/interuss/automated_testing/flight_planning.md)**.

## Failure If Planned check

Flight intent data of a nearby flight shared was invalid, but the result was planned. It should have been been failed.
If the USS indicates that the injection did not fail, this check will fail per
**[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../../../requirements/interuss/automated_testing/flight_planning.md)**.

## Failure If Conflict check
Flight intent data of a nearby flight shared was invalid, but the result was conflict with flight. It should have been been failed.
If the USS indicates that the injection did not fail, this check will fail per
**[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../../../requirements/interuss/automated_testing/flight_planning.md)**.

## Failure If Rejected check

Flight intent data of a nearby flight shared was invalid, but the result rejected. It should have been been failed.
If the USS indicates that the injection did not fail, this check will fail per
**[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../../../requirements/interuss/automated_testing/flight_planning.md)**.
