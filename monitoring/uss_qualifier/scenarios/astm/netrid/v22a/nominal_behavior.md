# ASTM NetRID nominal behavior test scenario

## Overview

In this scenario, a single nominal flight is injected into each NetRID Service Provider (SP) under test.  Each of the injected flights is expected to be visible to all the observers at appropriate times and for appropriate requests.

## Resources

### flights_data

A [`FlightDataResource`](../../../../resources/netrid/flight_data.py) containing 1 nominal flight per SP under test.

### service_providers

A set of [`NetRIDServiceProviders`](../../../../resources/netrid/service_providers.py) to be tested via the injection of RID flight data.  This scenario requires at least one SP under test.

### observers

A set of [`NetRIDObserversResource`](../../../../resources/netrid/observers.py) to be tested via checking their observations of the NetRID system and comparing the observations against expectations.  An observer generally represents a "Display Application", in ASTM F3411 terminology.  This scenario requires at least one observer.

### evaluation_configuration

This [`EvaluationConfigurationResource`](../../../../resources/netrid/evaluation.py) defines how to gauge success when observing the injected flights.

### dss_pool

If specified, uss_qualifier will act as a Display Provider and check a DSS instance from this [`DSSInstanceResource`](../../../../resources/astm/f3411/dss.py) for appropriate identification service areas and then query the corresponding USSs with flights using the same session.

## Nominal flight test case

### Injection test step

In this step, uss_qualifier injects a single nominal flight into each SP under test, usually with a start time in the future.  Each SP is expected to queue the provided telemetry and later simulate that telemetry coming from an aircraft at the designated timestamps.

#### Successful injection check

Per **[interuss.automated_testing.rid.injection.UpsertTestSuccess](../../../../requirements/interuss/automated_testing/rid/injection.md)**, the injection attempt of the valid flight should succeed for every NetRID Service Provider under test.

**[astm.f3411.v22a.NET0500](../../../../requirements/astm/f3411/v22a.md)** requires a Service Provider to provide a persistently supported test instance of their implementation.
This check will fail if the flight was not successfully injected.

#### Valid flight check

TODO: Validate injected flights, especially to make sure they contain the specified injection IDs

Per **[interuss.automated_testing.rid.injection.UpsertTestResult](../../../../requirements/interuss/automated_testing/rid/injection.md)**, the NetRID Service Provider under test should only make valid modifications to the injected flights.  This includes:
* A flight with the specified injection ID must be returned.

#### Identifiable flights check

This particular test requires each flight to be uniquely identifiable by its 2D telemetry position; the same (lat, lng) pair may not appear in two different telemetry points, even if the two points are in different injected flights.  This should generally be achieved by injecting appropriate data.

### Service Provider polling test step

If a DSS was provided to this test scenario, uss_qualifier acts as a Display Provider to query Service Providers under test in this step.

#### Recent positions timestamps check
**[astm.f3411.v22a.NET0270](../../../../requirements/astm/f3411/v22a.md)** requires all recent positions to be within the NetMaxNearRealTimeDataPeriod. This check will fail if any of the reported positions are older than the maximally allowed period plus NetSpDataResponseTime99thPercentile.

#### Recent positions for aircraft crossing the requested area boundary show only one position before or after crossing check
**[astm.f3411.v22a.NET0270](../../../../requirements/astm/f3411/v22a.md)** requires that when an aircraft enters or leaves the queried area, the last or first reported position outside the area is provided in the recent positions, as long as it is not older than NetMaxNearRealTimeDataPeriod.

This implies that any recent position outside the area must be either preceded or followed by a position inside the area.

(This check validates NET0270 b and c).

#### Flights data format check

**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** and **[astm.f3411.v22a.NET0340](../../../../requirements/astm/f3411/v22a.md)** requires a Service Provider to implement the P2P portion of the OpenAPI specification. This check will fail if the response to the /flights endpoint does not validate against the OpenAPI-specified schema.

#### ISA query check

**[interuss.f3411.dss_endpoints.SearchISAs](../../../../requirements/interuss/f3411/dss_endpoints.md)** requires a USS providing a DSS instance to implement the DSS endpoints of the OpenAPI specification.  If uss_qualifier is unable to query the DSS for ISAs, this check will fail.

#### Premature flight check

The timestamps of the injected telemetry usually start in the future.  If a flight with injected telemetry only in the future is observed prior to the timestamp of the first telemetry point, this check will fail because the SP does not satisfy **[interuss.automated_testing.rid.injection.ExpectedBehavior](../../../../requirements/interuss/automated_testing/rid/injection.md)**.

#### Missing flight check

**[astm.f3411.v22a.NET0610](../../../../requirements/astm/f3411/v22a.md)** requires that SPs make all UAS operations discoverable over the duration of the flight plus *NetMaxNearRealTimeDataPeriod*, so each injected flight should be observable during this time.  If a flight is not observed during its appropriate time period, this check will fail.

**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** and **[astm.f3411.v22a.NET0340](../../../../requirements/astm/f3411/v22a.md) require a Service Provider to implement the GET flights endpoint.  This check will also fail if uss_qualifier cannot query that endpoint (specified in the ISA present in the DSS) successfully.

The identity of flights is determined by precisely matching the known injected positions.  If the flight can be found, the USS may not have met **[astm.f3411.v22a.NET0260,Table1,10](../../../../requirements/astm/f3411/v22a.md)** or **[astm.f3411.v22a.NET0260,Table1,11](../../../../requirements/astm/f3411/v22a.md)** prescribing provision of position data consistent with the common data dictionary.

#### Service Provider altitude check

**[astm.f3411.v22a.NET0260,Table1,12](../../../../requirements/astm/f3411/v22a.md)** requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider.  Injected flight data had known altitudes, but the altitude reported by the Service Provider did not match those known altitudes.

#### Successful flight details query check

**[astm.f3411.v22a.NET0710,2](../../../../requirements/astm/f3411/v22a.md)** and **[astm.f3411.v22a.NET0340](../../../../requirements/astm/f3411/v22a.md) require a Service Provider to implement the GET flight details endpoint.  This check will fail if uss_qualifier cannot query that endpoint (specified in the ISA present in the DSS) successfully.

#### Flight details data format check

**[astm.f3411.v22a.NET0710,2](../../../../requirements/astm/f3411/v22a.md)** and **[astm.f3411.v22a.NET0340](../../../../requirements/astm/f3411/v22a.md) require a Service Provider to implement the P2P portion of the OpenAPI specification.  This check will fail if the response to the flight details endpoint does not validate against the OpenAPI-specified schema.

#### UAS ID presence in flight details check

NET0260 requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider. This check validates that the UAS ID is present in the information sent by the Service Provider. (**[astm.f3411.v22a.NET0260,Table1,1](../../../../requirements/astm/f3411/v22a.md)**)

#### UAS ID (Serial Number format) consistency with Common Dictionary check

NET0260 requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider. This check validates that the UAS ID is in serial number format. (**[astm.f3411.v22a.NET0260,Table1,1a](../../../../requirements/astm/f3411/v22a.md)**)

#### Operator ID consistency with Common Dictionary check

NET0260 requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider. This check validates that the Operator ID, if present, is expressed as ASCII text. (**[astm.f3411.v22a.NET0260,Table1,9](../../../../requirements/astm/f3411/v22a.md)**)

#### Operator Location consistency with Common Dictionary check

NET0260 requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider. This check validates that the Operator Latitude (**[astm.f3411.v22a.NET0260,Table1,23](../../../../requirements/astm/f3411/v22a.md)**) and Longitude (**[astm.f3411.v22a.NET0260,Table1,24](../../../../requirements/astm/f3411/v22a.md)**), if present, are valid.

#### Operator Altitude consistency with Common Dictionary check

NET0260 requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider. This check validates that if the Operator Altitude is based on WGS-84 height above ellipsoid (HAE) and is provided in meters. (**[astm.f3411.v22a.NET0260,Table1,25](../../../../requirements/astm/f3411/v22a.md)**)

#### Operator Altitude Type consistency with Common Dictionary check

NET0260 requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider. This check validates that if the Operator Altitude Type is valid, if present. (**[astm.f3411.v22a.NET0260,Table1,26](../../../../requirements/astm/f3411/v22a.md)**)

#### Operational Status consistency with Common Dictionary check

NET0260 requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider. This check validates that the Operational Status, if present, is valid. (**[astm.f3411.v22a.NET0260,Table1,7](../../../../requirements/astm/f3411/v22a.md)**)

#### Operational Status is consistent with injected one check

If the Operational status reported for an observation does not correspond to the injected one, the DP is not providing timely and accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**

#### Lingering flight check

**[astm.f3411.v22a.NET0270](../../../../requirements/astm/f3411/v22a.md)** requires a SP to provide flights up to *NetMaxNearRealTimeDataPeriod* in the past, but an SP should preserve privacy and ensure relevancy by not sharing flights that are further in the past than this window.

#### Area too large check

**[astm.f3411.v22a.NET0430](../../../../requirements/astm/f3411/v22a.md)** requires that a NetRID Display Provider rejects a request for a very large view area with a diagonal greater than *NetMaxDisplayAreaDiagonal*.  If such a large view is requested and a 413 error code is not received, then this check will fail.

### Observer polling test step

In this step, all observers are queried for the flights they observe.  Based on the known flights that were injected into the SPs in the first step, these observations are checked against expected behavior/data.  Observation rectangles are chosen to encompass the known flights when possible.

#### Successful observation check

Per **[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)**, the call to each observer is expected to succeed since a valid view was provided by uss_qualifier.

#### Duplicate flights check

Per **[interuss.automated_testing.rid.observation.UniqueFlights](../../../../requirements/interuss/automated_testing/rid/observation.md)**, the same flight ID may not be reported by a Display Provider for two flights in the same observation.

#### Premature flight check

The timestamps of the injected telemetry usually start in the future.  If a flight with injected telemetry only in the future is observed prior to the timestamp of the first telemetry point, this check will fail because the SP does not satisfy **[interuss.automated_testing.rid.injection.ExpectedBehavior](../../../../requirements/interuss/automated_testing/rid/injection.md)**.

#### Missing flight check

**[astm.f3411.v22a.NET0610](../../../../requirements/astm/f3411/v22a.md)** require that SPs make all UAS operations discoverable over the duration of the flight plus *NetMaxNearRealTimeDataPeriod*, so each injected flight should be observable during this time.  If one of the flights is not observed during its appropriate time period, this check will fail.

#### Lingering flight check

NET0260 requires a SP to provide flights up to *NetMaxNearRealTimeDataPeriod* in the past, but an SP should preserve privacy and ensure relevancy by not sharing flights that are further in the past than this window.

#### Telemetry being used when present check

**[astm.f3411.v22a.NET0290](../../../../requirements/astm/f3411/v22a.md)** requires a SP uses Telemetry vs extrapolation when telemetry is present.

#### Correct up-to-date altitude if present check

If the observed altitude of a flight is reported, but it does not match the altitude of the injected telemetry, the display provider is not providing precise and up-to-date information, and thus does not respect **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**.

#### Area too large check

**[astm.f3411.v22a.NET0430](../../../../requirements/astm/f3411/v22a.md)** require that a NetRID Display Provider reject a request for a very large view area with a diagonal greater than *NetMaxDisplayAreaDiagonal*.  If such a large view is requested and a 413 error code is not received, then this check will fail.

#### Minimal obfuscation distance of individual flights check

For a display area with a diagonal greater than *NetDetailsMaxDisplayAreaDiagonal* and less than *NetMaxDisplayAreaDiagonal*, **[astm.f3411.v22a.NET0490](../../../../requirements/astm/f3411/v22a.md)** requires that a Display provider shall obfuscate individual UAs within a cluster.
If a cluster with a single flight has a width or height smaller than 2 * *NetMinObfuscationDistance* (meaning that the USS did not buffer the single point by *NetMinObfuscationDistance* in all directions when forming the cluster bounds), this test will fail.

#### Individual flights obfuscation check

For a display area with a diagonal greater than *NetDetailsMaxDisplayAreaDiagonal* and less than *NetMaxDisplayAreaDiagonal*, **[astm.f3411.v22a.NET0490](../../../../requirements/astm/f3411/v22a.md)** requires that a Display provider shall obfuscate individual UAs within a cluster.
If a cluster with a single flight has its center equal to the position of the flight, this test will fail.
If a cluster with a single flight does not actually encompass the flight, this test will fail.

#### Minimal obfuscation distance of multiple flights clusters check

For a display area with a diagonal greater than *NetDetailsMaxDisplayAreaDiagonal* and less than *NetMaxDisplayAreaDiagonal*, **[astm.f3411.v22a.NET0480](../../../../requirements/astm/f3411/v22a.md)** requires that a Display provider shall cluster UAs in close proximity to each other using a circular or polygonal area.
If a cluster with multiples flights has a width or height smaller than 2 * *NetMinObfuscationDistance*, this test will fail. A larger width or height might still be incorrect, but the test cannot at the moment determine this.

#### Clustering count check

For a display area with a diagonal greater than *NetDetailsMaxDisplayAreaDiagonal* and less than *NetMaxDisplayAreaDiagonal*, **[astm.f3411.v22a.NET0480](../../../../requirements/astm/f3411/v22a.md)** requires that a Display provider shall cluster UAs in close proximity to each other using a circular or polygonal area.
Taking into account the propagation time of the injected flights, if the total number of clustered UAs when this value is expected to be stable is not correct, this test will fail.

#### Minimal display area of clusters check

For a display area with a diagonal greather than *NetDetailsMaxDisplayAreaDiagonal* and less than *NetMaxDisplayAreaDiagonal*, **[astm.f3411.v22a.NET0480](../../../../requirements/astm/f3411/v22a.md)** requires that a Display provider shall cluster UAs in close proximity to each other using a circular or polygonal area covering no less than *NetMinClusterSize* percent of the display area size.
This check validates that the display area of a cluster, measured and provided in square meters by the test harness, is no less than *NetMinClusterSize* percent of the display area.

#### Successful details observation check

Per **[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)**, the call for flight details is expected to succeed since a valid ID was provided by uss_qualifier.

#### UAS ID presence in flight details check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that the UAS ID is present in the information sent by the Display Provider. (**[astm.f3411.v22a.NET0470,Table1,1](../../../../requirements/astm/f3411/v22a.md)**)

#### UAS ID (Serial Number format) consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that if the UAS ID is in serial number format, its format is valid. (**[astm.f3411.v22a.NET0470,Table1,1a](../../../../requirements/astm/f3411/v22a.md)**)

#### UAS ID is consistent with injected one check

If the UAS ID contained in flight details returned by a display provider does not correspond to the injected one, the DP is not providing accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**

#### Timestamp consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that timestamps are relative to UTC. (**[astm.f3411.v22a.NET0470,Table1,5](../../../../requirements/astm/f3411/v22a.md)**)

#### Observed timestamp is consistent with injected one check

If the timestamp reported for an observation does not correspond to the injected one, the DP is not providing timely and accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**

#### Operational Status consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that the Operational Status, if present, is valid. (**[astm.f3411.v22a.NET0470,Table1,7](../../../../requirements/astm/f3411/v22a.md)**)

#### Operator ID consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall (NET0470) provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that the Operator ID, if present, is valid. (**[astm.f3411.v22a.NET0470,Table1,9](../../../../requirements/astm/f3411/v22a.md)**)

#### Operator ID is consistent with injected one check

If the Operator ID contained in flight details returned by a display provider does not correspond to the injected one, the DP is not providing accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**

#### Current Position consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that the Current Position provided is valid. (**[astm.f3411.v22a.NET0470,Table1,10](../../../../requirements/astm/f3411/v22a.md)** and **[astm.f3411.v22a.NET0470,Table1,11](../../../../requirements/astm/f3411/v22a.md)**). If the observed Current Position do not contain valid latitude and longitude, this check will fail.
TODO: If the resolution is greater than 7 number digits, this check will fail.

#### Observed Position is consistent with injected one check

If the Position reported for an observation does not correspond to the injected one, the DP is not providing timely and accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**

#### Height Type consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that the Height Type (**[astm.f3411.v22a.NET0470,Table1,15](../../../../requirements/astm/f3411/v22a.md)**), if present, is valid. If the observed Height Type indicates a value different than Takeoff Location or Ground Level, this check will fail.

#### Height is consistent with injected one check

If the Height Type reported for an observation does not correspond to the injected one, the DP is not providing timely and accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**

#### Track Direction consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that the Track Direction (**[astm.f3411.v22a.NET0470,Table1,19](../../../../requirements/astm/f3411/v22a.md)**) is valid. If the observed Track Direction is less than -359 or is greater than 359, except for the special value 361, this check will fail.

#### Observed track is consistent with injected one check

If the track reported for an observation does not correspond to the injected one, the DP is not providing timely and accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**

#### Speed consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that the Speed (**[astm.f3411.v22a.NET0470,Table1,20](../../../../requirements/astm/f3411/v22a.md)**) is valid. If the observed Speed is negative or greater than 254.25, except for the special value 255, this check will fail.

#### Observed speed is consistent with injected one check

If the speed reported for an observation does not correspond to the injected one, the DP is not providing timely and accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**

#### Operator Location consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that the Operator Latitude (**[astm.f3411.v22a.NET0470,Table1,23](../../../../requirements/astm/f3411/v22a.md)**) and Longitude (**[astm.f3411.v22a.NET0470,Table1,24](../../../../requirements/astm/f3411/v22a.md)**), if present, are valid.

#### Operator Location is consistent with injected one check

If the Operator Location contained in flight details returned by a display provider does not correspond to the injected one, the DP is not providing accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**

#### Operator Altitude consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that, if present, the Operator Altitude is based on WGS-84 height above ellipsoid (HAE) and is provided in meters. (**[astm.f3411.v22a.NET0470,Table1,25](../../../../requirements/astm/f3411/v22a.md)**)

#### Operator Altitude is consistent with injected one check

If the Operator Altitude contained in flight details returned by a display provider does not correspond to the injected one, the DP is not providing accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**

#### Operator Altitude Type consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that the Operator Altitude Type is valid, if present. (**[astm.f3411.v22a.NET0470,Table1,26](../../../../requirements/astm/f3411/v22a.md)**)

#### Operator Altitude Type is consistent with injected one check

If the Operator Altitude Type contained in flight details returned by a display provider does not correspond to the injected one, the DP is not providing accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**

## Cleanup

The cleanup phase of this test scenario attempts to remove injected data from all SPs.

### Successful test deletion check

**[interuss.automated_testing.rid.injection.DeleteTestSuccess](../../../../requirements/interuss/automated_testing/rid/injection.md)**
