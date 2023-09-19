# FAA LAANC Automated Testing USS-under-test requirements v1

This file documents the additional requirements a USS must satisfy in order to be tested for LAANC compliance using the InterUSS framework.

## Requirements

### <tt>FlightPlannerInterface</tt>

A USS wishing to be tested for LAANC compliance must implement the [InterUSS flight planning interface](https://github.com/interuss/automated_testing_interfaces/tree/main/flight_planning).  This interface allows the test director (uss_qualifier, when being tested by the InterUSS framework) to instruct the USS to emulate a user attempting to perform a flight planning activity (plan a new flight, update an existing flight, cancel an existing flight).

The USS should implement this interface exercising as much of their full system as possible.  For instance, in an extreme case, an incoming instruction (via this interface) to have a user create a flight might be translated into actuation of physical fingers on a robot interacting with a real tablet running the USS's application based on feedback from computer vision interpreting the tablet display.  In a less extreme case, that incoming instruction may instead be translated into a call to the USS's same backend API that is used by its frontend application to perform LAANC activities.  The implementation method for this interface will likely be of interest to the FAA when evaluating the extent to which automated testing demonstrates compliance to requirements.

The USS can expect the `additional_information` field in the request to be populated with the nested structure `faa.laanc.v7` which will have a field `rule_set` which will be populated to indicate what rule set the operator intends to fly under:
* `Part107`: Operator intends to fly under Part 107 rules
* `44809`: Operator intends to fly recreationally under section 44809 rules

### <tt>IncludeReferenceCode</tt>

When responding to a flight planning request that results in a new or updated LAANC authorization, the USS must include an additional field `faa_laanc_reference_code` in `UpsertFlightPlanResponse` specifying the LAANC authorization reference code available to the operator per 3.4.6b of the Performance Rules.
