# Plan flight Expect Failed test step fragment

This page describes the content of a common test case where a valid user flight intent fails in a flight planner, because of invalid data shared for a nearby flight shared by another USS.  See `plan_flight_intent_expect_failed` in invalid_op_test_steps.py.

## 🛑 Plan should fail check

A USS shouldn't go ahead and plan if it doesn't have accurate information.
As per SCD0035 a USS needs to verify a particular conflict status.
If flight intent data shared for a nearby flight shared is invalid, the USS can't successfully perform that verification.
It couldn't have obtained valid information about the other operational intents it's supposed to verify that conflict status against.
Therefore, the USS should fail an attempt to plan. If the plan succeeds, we know they've violated SCD0035 because they failed to verify that particular conflict status.

**[astm.f3548.v21.SCD0035](../../../../../requirements/astm/f3548/v21.md)**

