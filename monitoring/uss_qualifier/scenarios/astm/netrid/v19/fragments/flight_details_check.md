# Flight details check test step fragment

This test step fragment documents the validation of an injected test flight's details

## ⚠️ Flight details data format check

**[astm.f3411.v19.NET0710,2](../../../../../requirements/astm/f3411/v19.md)** and **[astm.f3411.v19.NET0340](../../../../../requirements/astm/f3411/v19.md) require a Service Provider to implement the P2P portion of the OpenAPI specification.  This check will fail if the response to the flight details endpoint does not validate against the OpenAPI-specified schema.

## ⚠️ Recent positions timestamps check

**[astm.f3411.v19.NET0270](../../../../../requirements/astm/f3411/v19.md)** requires all recent positions to be within the NetMaxNearRealTimeDataPeriod. This check will fail if any of the reported positions are older than the maximally allowed period plus NetSpDataResponseTime99thPercentile.
