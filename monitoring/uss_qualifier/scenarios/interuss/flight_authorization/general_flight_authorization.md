# General flight authorization test scenario

## Description

This test acts as a user using a USS's flight planning/authorization interface and attempts to plan/authorize different flights according to the Flight Check Table provided by the test designer (see `table` resource below), expecting these attempts to succeed or fail with or without advisories/conditions as defined by the test designer.  For instance, the test designer may include a Flight Check in their Flight Check table in an area known to be restricted, and then expect the planning/authorization attempt to fail.  But, when a similar plan/authorization is requested in an area that is known to be free of restrictions, this test would be expected to successfully plan/authorize a flight there.  More information may be seen [here](https://github.com/interuss/tsc/pull/7).

## Resources

### table

[Flight Check Table](../../../resources/interuss/flight_authorization/flight_check_table.py) consisting of a list of Flight Check rows.  Each Flight Check row will cause this test to attempt to plan/authorize a flight using the planning/authorization interfaces of each USS under test according to the information in that Flight Check row.  This test will then perform checks according to the expected outcomes from those planning/authorization attempts, according to the Flight Check row.

### flight_intents

[FlightIntentsResource](../../../resources/flight_planning/flight_intents_resource.py) defining all flight intents referenced by `table` above.

### planner

[Flight planner](../../../resources/flight_planning/flight_planners.py) providing access to the flight-planning USS under test in this scenario.

## Flight planning test case

### Dynamic test step

The test steps for this test scenario are generated dynamically according to the definitions in the Flight Check Table.  The checks for each step are the same and are documented below.

#### Valid planning response check

The USS under test is expected to implement the InterUSS flight_planning automated testing API and respond to requests accordingly.  If the USS does not respond to a flight planning request to this API properly, it will have failed to meet **[interuss.automated_testing.flight_planning.ImplementAPI](../../../requirements/interuss/automated_testing/flight_planning.md)**.

#### Disallowed flight check

When the test designer specifies that a particular Flight Check has an expected acceptance of "No", that means attempting to plan/authorize that flight in a USS should result in the request being rejected.  Upon this test making this request, if the USS successfully plans/authorizes the flight, this check will fail.

#### Allowed flight check

When the test designer specifies that a particular Flight Check has an expected acceptance of "Yes", that means attempting to plan/authorize that flight in a USS should result in the request being accepted.  Upon this test making this request, if the USS does not successfully plan/authorize the flight, this check will fail.

#### Required conditions check

When the test designer specifies that a particular Flight Check's conditions "MustBePresent", that means if a flight is successfully planned/authorized, it must be accompanied by conditions/advisories.  If a successfully-planned/authorized flight is not indicated to contain any conditions/advisories, this check will fail.

#### Disallowed conditions check

When the test designer specifies that a particular Flight Check's conditions "MustBeAbsent", that means if a flight is successfully planned/authorized, it must NOT be accompanied by any conditions/advisories.  If a successfully-planned/authorized flight IS indicated to contain any conditions/advisories, this check will fail.

#### Successful closure check

If a flight was successfully planned, then uss_qualifier will emulate a user attempting to close that flight.  The flight plan is expected to be Closed following that action.  If it is any other value, this check will fail per **[interuss.automated_testing.flight_planning.ExpectedBehavior](../../../requirements/interuss/automated_testing/flight_planning.md)**.  A value of NotPlanned is not acceptable because the flight had previously been planned.
