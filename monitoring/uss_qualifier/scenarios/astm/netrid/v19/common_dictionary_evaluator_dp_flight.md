# ASTM NetRID v19 Display Provider flight consistency with Common Data Dictionary test step fragment

This fragment is implemented in `common_dictionary_evaluator.py:RIDCommonDictionaryEvaluator.evaluate_dp_flight`.

#### Correct up-to-date altitude if present check

If the observed altitude of a flight is reported, but it does not match the altitude of the injected telemetry, the display provider is not providing precise and up-to-date information, and thus does not respect **[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)**.
