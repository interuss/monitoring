# ASTM NetRID v22a Service Provider flight details consistency with Common Data Dictionary test step fragment

This fragment is implemented in `common_dictionary_evaluator.py:RIDCommonDictionaryEvaluator.evaluate_sp_details`.

## ⚠️ UAS ID is exposed correctly check

If the UAS ID's serial number value exposed by the SP API is missing (serial number, registration ID, UTM ID or Specific session ID set) this check will fail per:
**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** because the SP violates the SP API contract;
**[astm.f3411.v22a.NET0260,Table1,1](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ UAS ID (Serial number) is exposed correctly check

If the UAS ID's serial number value exposed by the SP API is invalid this check will fail per:
**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** because the SP violates the SP API contract;
**[astm.f3411.v22a.NET0260,Table1,1a](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ UAS ID (Serial number) is consistent with injected value check

If the UAS ID's serial number value exposed by the SP API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v22a.NET0260,Table1,1a](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the valid injected value.

## ⚠️ UAS ID (Registration ID) is exposed correctly check

If the UAS ID's registration ID value exposed by the SP API is  invalid this check will fail per:
**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** because the SP violates the SP API contract;
**[astm.f3411.v22a.NET0260,Table1,1b](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ UAS ID (Registration ID) is consistent with injected value check

If the UAS ID's registration ID value exposed by the SP API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v22a.NET0260,Table1,1b](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the valid injected value.

## ⚠️ UAS ID (UTM ID) is exposed correctly check

If the UAS ID's UTM ID value exposed by the SP API is invalid this check will fail per:
**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** because the SP violates the SP API contract;
**[astm.f3411.v22a.NET0260,Table1,1c](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ UAS ID (UTM ID) is consistent with injected value check

If the UAS ID's UTM ID value exposed by the SP API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v22a.NET0260,Table1,1c](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the valid injected value.

## ⚠️ UAS ID (Specific session ID) is exposed correctly check

If the UAS ID's Specific session ID value exposed by the SP API is invalid this check will fail per:
**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** because the SP violates the SP API contract;
**[astm.f3411.v22a.NET0260,Table1,1d](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ UAS ID (Specific session ID) is consistent with injected value check

If the UAS ID's Specific session ID value exposed by the SP API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v22a.NET0260,Table1,1d](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the valid injected value.

If nothing has been injected, the SP is allowed to generate a value and thus this check is only done when UAS ID's UTM ID value has been injected.

## ⚠️ UA classification type is consistent with injected value check

If the UA classification type value exposed by the SP API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v22a.NET0260,Table1,4](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the valid injected value.

## ⚠️ UA classification 'category' field for 'European Union' type is exposed correctly check

If the UA classification 'category' field for 'European Union' type value exposed by the SP API is missing or invalid this check will fail per:
**[astm.f3411.v22a.NET0710,2](../../../../requirements/astm/f3411/v22a.md)** because the SP violates the SP API contract;
**[astm.f3411.v22a.NET0260,Table1,3](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ UA classification 'category' field for 'European Union' type is consistent with injected value check

If the UA classification 'category' field for 'European Union' type value exposed by the SP API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v22a.NET0260,Table1,3](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the valid injected value.

## ⚠️ UA classification 'class' field for 'European Union' type is exposed correctly check

If the UA classification 'class' field for 'European Union' type value exposed by the SP API is missing or invalid this check will fail per:
**[astm.f3411.v22a.NET0710,2](../../../../requirements/astm/f3411/v22a.md)** because the SP violates the SP API contract;
**[astm.f3411.v22a.NET0260,Table1,3](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ UA classification 'class' field for 'European Union' type is consistent with injected value check

If the UA classification 'class' field for 'European Union' type value exposed by the SP API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v22a.NET0260,Table1,3](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the valid injected value.

## ⚠️ Operator ID consistency with Common Dictionary check

NET0260 requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider. This check validates that the Operator ID, if present, is expressed as ASCII text. (**[astm.f3411.v22a.NET0260,Table1,9](../../../../requirements/astm/f3411/v22a.md)**)

## ⚠️ Operator Location consistency with Common Dictionary check

NET0260 requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider. This check validates that the Operator Latitude (**[astm.f3411.v22a.NET0260,Table1,23](../../../../requirements/astm/f3411/v22a.md)**) and Longitude (**[astm.f3411.v22a.NET0260,Table1,24](../../../../requirements/astm/f3411/v22a.md)**), if present, are valid.

## ⚠️ Operator Altitude consistency with Common Dictionary check

NET0260 requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider. This check validates that if the Operator Altitude is based on WGS-84 height above ellipsoid (HAE) and is provided in meters. (**[astm.f3411.v22a.NET0260,Table1,25](../../../../requirements/astm/f3411/v22a.md)**)

## ⚠️ Operator Altitude Type consistency with Common Dictionary check

NET0260 requires that relevant Remote ID data, consistent with the common data dictionary, be reported by the Service Provider. This check validates that if the Operator Altitude Type is valid, if present. (**[astm.f3411.v22a.NET0260,Table1,26](../../../../requirements/astm/f3411/v22a.md)**)
