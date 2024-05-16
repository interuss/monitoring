# Create nonconforming flight test step fragment

This page describes the content of a common test step where a valid user flight intent should be successfully created in the nonconforming state by a flight planner. 

Note that executing this test step requires the managing USS to support the CMSA role. As such, if the USS rejects the creation 
of the Nonconforming state, it will be assumed that the tested USS does not support this role and the test
execution will stop without failing.

#### 🛑 Failure check
All flight intent data provided is correct, therefore it should have been
created in the Nonconforming state by the USS
per **[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../../../requirements/interuss/automated_testing/flight_planning.md)**.
If the USS indicates that the injection attempt failed, this check will fail.
