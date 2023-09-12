# InterUSS RemoteID Injection Interface Requirements

## Overview

In order to test remote ID Service Providers (USSs who ingest aircraft data from operators and provide it to relevant Display Providers), InterUSS requires any Service Provider under test to implement the [InterUSS remote ID automated testing interface](https://github.com/interuss/automated_testing_interfaces/tree/main/rid) (specifically, the [injection portion](https://github.com/interuss/automated_testing_interfaces/blob/main/rid/v1/injection.yaml)).  This interface empowers uss_qualifier, as the test director, to instruct the USS to create a flight in a particular area with particular characteristics.  This is analogous to a similar verbal instruction during a manual checkout (e.g., "USS X, start your flight in the yellow area").

## Requirements

In general, to be successfully tested by uss_qualifier for remote ID functionality, Service Provider USSs are expected to implement the injection API mentioned above and successfully respond to valid requests.

### <tt>UpsertTestSuccess</tt>

When a properly-authorized valid request to create/start/simulate a set of flights ("test"), the USS under test must execute this request (create/start/simulate the flights) and indicate success.

### <tt>UpsertTestResult</tt>

The USS under test is allowed to modify most components of the requested flights including the telemetry and details responses, including the flight ID (though not the injection_id; that is the invariant ID by which uss_qualifier refers to an injected test flight).  However, there are obviously limits on how much the injected flight may be modified and still serve the purposes of the test being conducted.  For instance, a test whose purpose was to observe interactions between multiple providers' flights in the same area could not be accomplished if all but one USS created flights in a particular city in Europe while the last USS created their flight in the United States.  The actually-injected flight returned by the USS under test in response to an injection request must be suitable for the test to be conducted.  In practice, this means that USSs should modify the injection request as little as possible while still maintaining compatibility with their system.

### <tt>ExpectedBehavior</tt>

The USS under test must treat injected flights as similarly to real flights as practical.  The same pathways that accept real telemetry should be used to accept the injected telemetry.  For instance, the standard pathway to accept real telemetry should generally not accept reports from the future, so if future telemetry of the injected flight is visible appreciably before the time it is supposed to have been virtually reported then the USS into which the flight was injected is not treating the injected flight the same way a normal flight would be treated.

### <tt>DeleteTestSuccess</tt>

In order to rapidly conduct sequences of automated tests, uss_qualifier (as test director) must be able to "clear the airspace" after the completion of a test so that the simulated/injected flights from this test run do not affect future test runs.  A Service Provider USS must successfully cancel/land/remove/delete the flights in a specified test upon deletion request for that test and indicate success for the deletion request.
