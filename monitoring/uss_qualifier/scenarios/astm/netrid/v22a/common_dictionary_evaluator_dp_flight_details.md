# ASTM NetRID v22a Display Provider flight details consistency with Common Data Dictionary test step fragment

This fragment is implemented in `common_dictionary_evaluator.py:RIDCommonDictionaryEvaluator.evaluate_dp_details`.

## UAS ID presence in flight details check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that the UAS ID is present in the information sent by the Display Provider. (**[astm.f3411.v22a.NET0470,Table1,1](../../../../requirements/astm/f3411/v22a.md)**)

## UAS ID (Serial Number format) consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that if the UAS ID is in serial number format, its format is valid. (**[astm.f3411.v22a.NET0470,Table1,1a](../../../../requirements/astm/f3411/v22a.md)**)

## UAS ID is consistent with injected one check

If the UAS ID contained in flight details returned by a display provider does not correspond to the injected one, the DP is not providing accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**

## Operator ID consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall (NET0470) provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that the Operator ID, if present, is valid. (**[astm.f3411.v22a.NET0470,Table1,9](../../../../requirements/astm/f3411/v22a.md)**)

## Operator ID is consistent with injected one check

If the Operator ID contained in flight details returned by a display provider does not correspond to the injected one, the DP is not providing accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**

## Operator Location consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that the Operator Latitude (**[astm.f3411.v22a.NET0470,Table1,23](../../../../requirements/astm/f3411/v22a.md)**) and Longitude (**[astm.f3411.v22a.NET0470,Table1,24](../../../../requirements/astm/f3411/v22a.md)**), if present, are valid.

## Operator Location is consistent with injected one check

If the Operator Location contained in flight details returned by a display provider does not correspond to the injected one, the DP is not providing accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**

## Operator Altitude consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that, if present, the Operator Altitude is based on WGS-84 height above ellipsoid (HAE) and is provided in meters. (**[astm.f3411.v22a.NET0470,Table1,25](../../../../requirements/astm/f3411/v22a.md)**)

## Operator Altitude is consistent with injected one check

If the Operator Altitude contained in flight details returned by a display provider does not correspond to the injected one, the DP is not providing accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**

## Operator Altitude Type consistency with Common Dictionary check

**[astm.f3411.v22a.NET0470](../../../../requirements/astm/f3411/v22a.md)** requires that Net-RID Display Provider shall provide access to required and optional fields to Remote ID Display Applications according to the Common Dictionary. This check validates that the Operator Altitude Type is valid, if present. (**[astm.f3411.v22a.NET0470,Table1,26](../../../../requirements/astm/f3411/v22a.md)**)

## Operator Altitude Type is consistent with injected one check

If the Operator Altitude Type contained in flight details returned by a display provider does not correspond to the injected one, the DP is not providing accurate data and is thus in breach of **[astm.f3411.v22a.NET0450](../../../../requirements/astm/f3411/v22a.md)**
