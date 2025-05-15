# ASTM NetRID v19 flight presence test step fragment

This fragment is implemented in `display_data_evaluator.py:RIDObservationEvaluator._evaluate_flight_presence`.

#### ⚠️ Premature flight check

The timestamps of the injected telemetry usually start in the future.  If a flight with injected telemetry only in the future is observed prior to the timestamp of the first telemetry point, this check will fail because the SP does not satisfy **[interuss.automated_testing.rid.injection.ExpectedBehavior](../../../../requirements/interuss/automated_testing/rid/injection.md)**.

#### ⚠️ Missing flight check

**[astm.f3411.v19.NET0610](../../../../requirements/astm/f3411/v19.md)** requires that SPs make all UAS operations discoverable over the duration of the flight plus *NetMaxNearRealTimeDataPeriod*, so each injected flight should be observable during this time.  If a flight is not observed during its appropriate time period, this check will fail.

**[astm.f3411.v19.NET0710,1](../../../../requirements/astm/f3411/v19.md)** and **[astm.f3411.v19.NET0340](../../../../requirements/astm/f3411/v19.md)** require a Service Provider to implement the GET flights endpoint.  This check will also fail if uss_qualifier cannot query that endpoint (specified in the ISA present in the DSS) successfully.

The identity of flights is determined by precisely matching the known injected positions.  If the flight can be found, the USS may not have met **[astm.f3411.v19.NET0260,Table1,9](../../../../requirements/astm/f3411/v19.md)** or **[astm.f3411.v19.NET0260,Table1,10](../../../../requirements/astm/f3411/v19.md)** prescribing provision of position data consistent with the common data dictionary.

#### ⚠️ Lingering flight check

**[astm.f3411.v19.NET0260,NearRealTime](../../../../requirements/astm/f3411/v19.md)** requires a SP to provide flights up to *NetMaxNearRealTimeDataPeriod* in the past, but an SP should preserve privacy and ensure relevancy by not sharing flights that are further in the past than this window.
