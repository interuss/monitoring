# InterUSS Flight Planning Interface Requirements

## Overview

When a USS implements the [InterUSS flight_planning automated testing API](https://github.com/interuss/automated_testing_interfaces/tree/main/flight_planning) (or [legacy scd automated testing API](https://github.com/interuss/automated_testing_interfaces/tree/main/scd)), they are expected to respond to requests to that API as defined in the API.  Specific requirements are below.

## Requirements

### <tt>ImplementAPI</tt>

A USS must implement the endpoints defined in the API, accept requests in the data format prescribed in the API, and respond in the data format prescribed in the API.  If there is a problem using the API such as a connection error, invalid response code, or invalid data, the USS will have failed to meet this requirement.

### <tt>Readiness</tt>

A USS must implement the readiness endpoint defined in the API and then respond that it is ready to respond with an appropriate API version.

### <tt>ClearArea</tt>

In order to conduct automated tests effectively, the USS must remove all of their existing flights from a particular area when instructed by the test director.  This is not an action performed on behalf of an emulated user, but rather an action performed in any way appropriate to support automated testing -- therefore, fulfilling this request may cause actions on the implementing USS's system that no normal user would be able to perform.

### <tt>ExpectedBehavior</tt>

When the test director (client of the flight planning API; usually uss_qualifier) requests that a flight planning activity be performed, the API implementer must act as if this request is coming from a normal user attempting to use the USS's system normally.  The USS must fulfill this request as it would for a normal user, and these actions are generally expected to succeed (allowing the user to fly) when a UTM rule does not prohibit them.

### <tt>FlightCoveredByOperationalIntent</tt>

For InterUSS to effectively test the requirements of ASTM F3548-21, a USS under test must act as if there is a
regulatory requirement requiring all flights it manages to provide operational intents according to ASTM F3548-21 at all
times for all flights it manages.

### <tt>DeleteFlightSuccess</tt>

In order to conduct automated tests effectively, the USS must remove a particular flight when instructed by the test director.  This is not an action performed on behalf of an emulated user, but rather an action performed in any way appropriate to support automated testing -- therefore, fulfilling this request may cause actions on the implementing USS's system that no normal user would be able to perform.
