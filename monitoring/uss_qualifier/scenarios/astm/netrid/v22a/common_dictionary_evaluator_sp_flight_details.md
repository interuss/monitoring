# ASTM NetRID v22a Service Provider flight details consistency with Common Data Dictionary test step fragment

This fragment is implemented in `common_dictionary_evaluator.py:RIDCommonDictionaryEvaluator.evaluate_sp_details`.

## UAS ID presence in flight details check

NET0260 requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider. This check validates that the UAS ID is present in the information sent by the Service Provider. (**[astm.f3411.v22a.NET0260,Table1,1](../../../../requirements/astm/f3411/v22a.md)**)

## UAS ID (Serial Number format) consistency with Common Dictionary check

NET0260 requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider. This check validates that the UAS ID is in serial number format. (**[astm.f3411.v22a.NET0260,Table1,1a](../../../../requirements/astm/f3411/v22a.md)**)

## Operator ID consistency with Common Dictionary check

NET0260 requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider. This check validates that the Operator ID, if present, is expressed as ASCII text. (**[astm.f3411.v22a.NET0260,Table1,9](../../../../requirements/astm/f3411/v22a.md)**)

## Operator Location consistency with Common Dictionary check

NET0260 requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider. This check validates that the Operator Latitude (**[astm.f3411.v22a.NET0260,Table1,23](../../../../requirements/astm/f3411/v22a.md)**) and Longitude (**[astm.f3411.v22a.NET0260,Table1,24](../../../../requirements/astm/f3411/v22a.md)**), if present, are valid.

## Operator Altitude consistency with Common Dictionary check

NET0260 requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider. This check validates that if the Operator Altitude is based on WGS-84 height above ellipsoid (HAE) and is provided in meters. (**[astm.f3411.v22a.NET0260,Table1,25](../../../../requirements/astm/f3411/v22a.md)**)

## Operator Altitude Type consistency with Common Dictionary check

NET0260 requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider. This check validates that if the Operator Altitude Type is valid, if present. (**[astm.f3411.v22a.NET0260,Table1,26](../../../../requirements/astm/f3411/v22a.md)**)
