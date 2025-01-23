# ASTM NetRID v19 Display Provider flight consistency with Common Data Dictionary test step fragment

This fragment is implemented in `common_dictionary_evaluator.py:RIDCommonDictionaryEvaluator.evaluate_dp_flight`.

## ⚠️ UA type is exposed correctly check

If the UA type value exposed by the observation API is invalid this check will fail per:
**[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)** because the DP violates the observation API contract;
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,3](../../../../requirements/astm/f3411/v19.md)** because the DP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ UA type is consistent with injected value check

If the UA type value exposed by the observer API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,3](../../../../requirements/astm/f3411/v19.md)**  because the DP fails to expose data consistent with the valid injected value.

## ⚠️ Timestamp accuracy is exposed correctly check

If the Timestamp accuracy value exposed by the observation API is invalid this check will fail per:
**[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)** because the DP violates the observation API contract;
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,5](../../../../requirements/astm/f3411/v19.md)** because the DP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Timestamp accuracy is consistent with injected value check

If the Timestamp accuracy value exposed by the observer API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,5](../../../../requirements/astm/f3411/v19.md)**  because the DP fails to expose data consistent with the valid injected value.

## Correct up-to-date altitude if present check

If the observed altitude of a flight is reported, but it does not match the altitude of the injected telemetry, the display provider is not providing precise and up-to-date information, and thus does not respect **[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)**.
