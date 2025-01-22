# Service provider polling test step fragment

uss_qualifier acts as a Display Provider to query Service Providers under test in this step.

## ⚠️ ISA query check

**[interuss.f3411.dss_endpoints.SearchISAs](../../../../../requirements/interuss/f3411/dss_endpoints.md)** requires a USS providing a DSS instance to implement the DSS endpoints of the OpenAPI specification.  If uss_qualifier is unable to query the DSS for ISAs, this check will fail.

## ⚠️ Successful flight details query check

**[astm.f3411.v22a.NET0710,2](../../../../../requirements/astm/f3411/v22a.md)** and **[astm.f3411.v22a.NET0340](../../../../../requirements/astm/f3411/v22a.md) require a Service Provider to implement the GET flight details endpoint.  This check will fail if uss_qualifier cannot query that endpoint (specified in the ISA present in the DSS) successfully.

## [Flight presence checks](../display_data_evaluator_flight_presence.md)
