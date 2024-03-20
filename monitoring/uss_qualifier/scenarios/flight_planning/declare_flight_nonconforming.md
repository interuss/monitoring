# Declare flight non-conforming test step fragment

This page describes the content of a common test step where a valid user flight intent should be successfully declared non-conforming by a flight planner.  See `declare_flight_nonconforming` in [test_steps.py](test_steps.py).

## 🛑 Successfully declare flight non-conforming check

All flight intent data provided is correct and valid, therefore it should have been declared non-conforming by the USS per **[interuss.automated_testing.flight_planning.ExpectedBehavior](../../requirements/interuss/automated_testing/flight_planning.md)**.
If the USS indicates that the operation is not supported, *this check will be skipped*.
If the USS indicates anything other than a `Completed` result with an `OffNominal` flight plan status, this check will fail.

## 🛑 Failure check

All flight intent data provided was complete and correct. It should have been processed successfully, allowing the USS
to process the flight. If the USS indicates that the attempt failed, this check will fail per
**[interuss.automated_testing.flight_planning.ExpectedBehavior](../../requirements/interuss/automated_testing/flight_planning.md)**.
