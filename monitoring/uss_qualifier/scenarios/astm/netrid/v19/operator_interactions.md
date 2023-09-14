# ASTM NetRID: Operator interactions test scenario

## Overview

Set up situations in which operator interactions (notifications) are required, and verify that those notifications are observed for the USS under test.

Note that none of this scenario is implemented yet.

## Resources

## Future resources

### service_provider

A singular `NetRIDServiceProvider` to be tested via the injection of RID flight data.

TODO: Create this resource

### operator_notifications

Means by which to ask "What user/operator notifications have been observed for user/operator X (from the USS under test) over time period Z".

TODO: Create this resource

### flights_data

A [`FlightDataResource`](../../../../resources/netrid/flight_data.py) containing 1 flight.  This flight must:
* (Phase 1): Start out nominal
* (Phase 2): Then contain a pause (lack of telemetry) sufficient to trigger NET0040
* (Phase 3): Then resume nominal telemetry
* (Phase 4): Then contain insufficient data to trigger NET0030

### orchestrated_dss

A DSS instance that is equipped to fail on command, and will be used by the USS under test.

TODO: Create this resource

## Failed ISA test case

### Verify no ISAs test step

uss_qualifier checks the DSS to ensure that the Service Provider under test does not have any ISAs in the system.  If ISAs are present, the Service Provider is instructed to clear the area of active flights, after which uss_qualifier reverifies the absence of ISAs.

### Disable DSS test step

uss_qualifier commands the orchestrated DSS to fail when interacting with normal clients.

### Enumerate pre-existing operator notifications test step

uss_qualifier retrieves the current (pre-existing) set of operator notifications.

### Inject flight test step

uss_qualifier attempts to inject a flight into the Service Provider under test, knowing that the Service Provider will not be able to create an ISA.

#### Flight failed check

Since the DSS is known to fail when attempting to create an ISA, if the Service Provider successfully creates the flight, they will have not met **[astm.f3411.v19.NET0610](../../../../requirements/astm/f3411/v19.md)**.

TODO: Implement

### Enumerate operator notifications test step

uss_qualifier retrieves the current (after failed flight) set of operator notifications.

#### Operator notified of discoverability failure check

The "after" set of operator notifications should contain at least one more entry than the "before" set of operator notifications.  If there was no new operator notification, the Service Provider will not have met **[astm.f3411.v19.NET0620](../../../../requirements/astm/f3411/v19.md)**.

TODO: Implement

## In-flight notifications test case

### Inject flight test step

uss_qualifier injects the flight into the Service Provider under test with the intention of observing the whole flight.

### Enumerate pre-existing operator notifications test step

uss_qualifier retrieves the current (pre-existing) set of operator notifications.

### Poll Service Provider test step

Throughout the duration of the flight, uss_qualifier periodically polls for operator notifications.

#### Insufficient telemetry operator notification check

If the Service Provider under test does not provide an operator notification in Phase 2 (regarding the telemetry feed stopping), it will not have complied with **[astm.f3411.v19.NET0040](../../../../requirements/astm/f3411/v19.md)**.

TODO: Implement

#### Missing data operator notification check

If the Service Provider under test does not provide an operator notification in Phase 4 (regarding missing data fields in reported telemetry), it will not have complied with **[astm.f3411.v19.NET0030](../../../../requirements/astm/f3411/v19.md)**.

TODO: Implement
