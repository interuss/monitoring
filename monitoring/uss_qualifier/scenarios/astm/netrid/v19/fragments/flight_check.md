# Flight check test step fragment

This test step fragment documents the validation of an injected test flight

## ⚠️ Flights data format check

**[astm.f3411.v19.NET0710,1](../../../../../requirements/astm/f3411/v19.md)** and **[astm.f3411.v19.NET0340](../../../../../requirements/astm/f3411/v19.md)** requires a Service Provider to implement the P2P portion of the OpenAPI specification. This check will fail if the response to the /flights endpoint does not validate against the OpenAPI-specified schema.


## ⚠️ Recent positions for aircraft crossing the requested area boundary show only one position before or after crossing check

**[astm.f3411.v19.NET0270](../../../../../requirements/astm/f3411/v19.md)** requires that when an aircraft enters or leaves the queried area, the last or first reported position outside the area is provided in the recent positions, as long as it is not older than NetMaxNearRealTimeDataPeriod.

This implies that any recent position outside the area must be either preceded or followed by a position inside the area.

(This check validates NET0270 b and c).

## [Flight consistency with Common Data Dictionary checks](../common_dictionary_evaluator_sp_flight.md)

