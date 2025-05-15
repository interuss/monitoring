# Flight injection test step fragment

This test step fragment documents the injection of test flights.

In this step, uss_qualifier injects a single nominal flight into each SP under test, usually with a start time in the future.  Each SP is expected to queue the provided telemetry and later simulate that telemetry coming from an aircraft at the designated timestamps.

## 🛑 Successful injection check

Per **[interuss.automated_testing.rid.injection.UpsertTestSuccess](../../../../../requirements/interuss/automated_testing/rid/injection.md)**, the injection attempt of the valid flight should succeed for every NetRID Service Provider under test.

**[astm.f3411.v19.NET0500](../../../../../requirements/astm/f3411/v19.md)** requires a Service Provider to provide a persistently supported test instance of their implementation.
This check will fail if the flight was not successfully injected.

## 🛑 Identifiable flights check

This particular test requires each flight to be uniquely identifiable by its 2D telemetry position; the same (lat, lng) pair may not appear in two different telemetry points, even if the two points are in different injected flights.  This should generally be achieved by injecting appropriate data.

## 🛑 Valid flight check

TODO: Validate injected flights, especially to make sure they contain the specified injection IDs

Per **[interuss.automated_testing.rid.injection.UpsertTestResult](../../../../../requirements/interuss/automated_testing/rid/injection.md)**, the NetRID Service Provider under test should only make valid modifications to the injected flights.  This includes:
* A flight with the specified injection ID must be returned.
