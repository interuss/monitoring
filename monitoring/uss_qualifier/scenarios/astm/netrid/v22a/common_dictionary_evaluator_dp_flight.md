# ASTM NetRID v22a Display Provider flight consistency with Common Data Dictionary test step fragment

This fragment is implemented in `common_dictionary_evaluator.py:RIDCommonDictionaryEvaluator.evaluate_dp_flight`.

## Correct up-to-date altitude if present check

If the observed altitude of a flight is reported, but it does not match the altitude of the injected telemetry, the display provider is not providing precise and up-to-date information, and thus does not respect **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**.

## Timestamp consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that timestamps are relative to UTC. (**[astm.f3411.v22a.NET0470,Table1,5](../../../../requirements/astm/f3411/v22a.md)**)

## Observed timestamp is consistent with injected one check

If the timestamp reported for an observation does not correspond to the injected one, the DP is not providing timely and accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**

## Operational Status consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that the Operational Status, if present, is valid. (**[astm.f3411.v22a.NET0470,Table1,7](../../../../requirements/astm/f3411/v22a.md)**)

## Current Position consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that the Current Position provided is valid. (**[astm.f3411.v22a.NET0470,Table1,10](../../../../requirements/astm/f3411/v22a.md)** and **[astm.f3411.v22a.NET0470,Table1,11](../../../../requirements/astm/f3411/v22a.md)**). If the observed Current Position do not contain valid latitude and longitude, this check will fail.
TODO: If the resolution is greater than 7 number digits, this check will fail.

## Observed Position is consistent with injected one check

If the Position reported for an observation does not correspond to the injected one, the DP is not providing timely and accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**

## Height consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that the Height (**[astm.f3411.v22a.NET0470,Table1,14](../../../../requirements/astm/f3411/v22a.md)**), if present, is valid.

## Height is consistent with injected one check

If the Height reported for an observation does not correspond to the injected one, the DP is not providing timely and accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**

## Height Type consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that the Height Type (**[astm.f3411.v22a.NET0470,Table1,15](../../../../requirements/astm/f3411/v22a.md)**), if present, is valid. If the observed Height Type indicates a value different than Takeoff Location or Ground Level, this check will fail.

## Height Type is consistent with injected one check

If the Height Type reported for an observation does not correspond to the injected one, the DP is not providing timely and accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**

## Track Direction consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that the Track Direction (**[astm.f3411.v22a.NET0470,Table1,19](../../../../requirements/astm/f3411/v22a.md)**) is valid. If the observed Track Direction is less than -359 or is greater than 359, except for the special value 361, this check will fail.

## Observed track is consistent with injected one check

If the track reported for an observation does not correspond to the injected one, the DP is not providing timely and accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**

## Speed consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that the Speed (**[astm.f3411.v22a.NET0470,Table1,20](../../../../requirements/astm/f3411/v22a.md)**) is valid. If the observed Speed is negative or greater than 254.25, except for the special value 255, this check will fail.

## Observed speed is consistent with injected one check

If the speed reported for an observation does not correspond to the injected one, the DP is not providing timely and accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**
