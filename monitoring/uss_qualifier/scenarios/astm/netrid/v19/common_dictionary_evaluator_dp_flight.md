# ASTM NetRID v19 Display Provider flight consistency with Common Data Dictionary test step fragment

This fragment is implemented in `common_dictionary_evaluator.py:RIDCommonDictionaryEvaluator.evaluate_dp_flight`.

## ⚠️ UA type is present and consistent with injected one check

**[astm.f3411.v19.NET0470](../../../../requirements/astm/f3411/v19.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary.
The UA type being a required field, this check will fail as per **[astm.f3411.v19.NET0470,Table1,3](../../../../requirements/astm/f3411/v19.md)** if it is missing.
In addition, if the UA type reported for an observation does not correspond to the injected one, the DP is not providing timely and accurate data and is thus in breach of **[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)**

## ⚠️ UA type is consistent with Common Data Dictionary check

**[astm.f3411.v19.NET0470](../../../../requirements/astm/f3411/v19.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary.
This check will fail if the observed UA type has an invalid value as per **[astm.f3411.v19.NET0470,Table1,3](../../../../requirements/astm/f3411/v19.md)**.

## Correct up-to-date altitude if present check

If the observed altitude of a flight is reported, but it does not match the altitude of the injected telemetry, the display provider is not providing precise and up-to-date information, and thus does not respect **[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)**.
