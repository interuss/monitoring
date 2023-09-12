# InterUSS RemoteID Observation Interface Requirements

## Overview

In order to test remote ID Display Providers (USSs who obtain aircraft data from Service Providers in order to aggregate it for their end-user viewers), InterUSS requires any Display Provider under test to implement the [InterUSS remote ID automated testing interface](https://github.com/interuss/automated_testing_interfaces/tree/main/rid) (specifically, the [observation portion](https://github.com/interuss/automated_testing_interfaces/blob/main/rid/v1/observation.yaml)).  This interface empowers uss_qualifier, as the test director, to ask the USS what flights would be visible on its Display Application(s).  This is analogous to a similar verbal question during a manual checkout (e.g., "USS Y, what flights do you see in the yellow area?").

## Requirements

In general, to be successfully tested by uss_qualifier for remote ID functionality, Display Provider USSs are expected to implement the observation API mentioned above and successfully respond to valid requests.

### <tt>ObservationSuccess</tt>

Upon receipt of a properly-authorized valid request to report the flights visible in a particular area, the USS under test must respond with the content visible in that area.  Even if the user/viewer would be shown an error or other off-nominal situation in the Display Application, it should still be possible to return a valid response to this question (e.g., in the case of the user being shown an error, the USS would indicate no flights and no cluster visible).

### <tt>UniqueFlights</tt>

While the identifiers for displayed flights are an implementation detail of the USS (it may use NetRID identifiers, or it may assign different identifiers), the user/viewer needs the capability to obtain details about a specific individual flight.  For that reason, a USS must provide unique identifiers for each flight in a particular observation.
