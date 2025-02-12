# ASTM NetRID v22a Service Provider flight consistency with Common Data Dictionary test step fragment

This fragment is implemented in `common_dictionary_evaluator.py:RIDCommonDictionaryEvaluator.evaluate_sp_flight`.

## ⚠️ UA type is exposed correctly check

If the UA type value exposed by the SP API is missing or invalid this check will fail per:
**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** because the SP violates the SP API contract;
**[astm.f3411.v22a.NET0260,Table1,2](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ UA type is consistent with injected value check

If the UA type value exposed by the SP API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v22a.NET0260,Table1,2](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the valid injected value.

## ⚠️ Timestamp is exposed correctly check

If the Timestamp value exposed by the SP API is missing or invalid this check will fail per:
**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** because the SP violates the SP API contract;
**[astm.f3411.v22a.NET0260,Table1,5](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Timestamp is consistent with injected value check

If the Timestamp value exposed by the SP API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v22a.NET0260,Table1,5](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the valid injected value.

## ⚠️ Timestamp accuracy is exposed correctly check

If the Timestamp accuracy value exposed by the SP API is missing or invalid this check will fail per:
**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** because the SP violates the SP API contract;
**[astm.f3411.v22a.NET0260,Table1,6](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Timestamp accuracy is consistent with injected value check

If the Timestamp accuracy value exposed by the SP API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v22a.NET0260,Table1,6](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the valid injected value.

## ⚠️ Operational status is exposed correctly check

If the Operational status value exposed by the SP API is missing or invalid this check will fail per:
**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** because the SP violates the SP API contract;
**[astm.f3411.v22a.NET0260,Table1,7](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Operational status is consistent with injected value check

If the Operational status value exposed by the SP API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v22a.NET0260,Table1,7](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the valid injected value.

## ⚠️ Geodetic Altitude is exposed correctly check

If the Geodetic Altitude value exposed by the SP API is missing or invalid this check will fail per:
**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** because the SP violates the SP API contract;
**[astm.f3411.v22a.NET0260,Table1,12](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Geodetic Altitude is consistent with injected value check

If the Geodetic Altitude value exposed by the SP API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v22a.NET0260,Table1,12](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the valid injected value.

## ⚠️ Height is exposed correctly check

If the Height value exposed by the SP API is missing or invalid this check will fail per:
**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** because the SP violates the SP API contract;
**[astm.f3411.v22a.NET0260,Table1,14](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Height is consistent with injected value check

If the Height value exposed by the SP API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v22a.NET0260,Table1,14](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the valid injected value.

## ⚠️ Height type is exposed correctly check

If the Height type value exposed by the SP API is missing or invalid this check will fail per:
**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** because the SP violates the SP API contract;
**[astm.f3411.v22a.NET0260,Table1,15](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Height type is consistent with injected value check

If the Height type value exposed by the SP API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v22a.NET0260,Table1,15](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the valid injected value.

## ⚠️ Geodetic Vertical Accuracy is exposed correctly check

If the Geodetic Vertical Accuracy value exposed by the SP API is missing or invalid this check will fail per:
**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** because the SP violates the SP API contract;
**[astm.f3411.v22a.NET0260,Table1,16](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Geodetic Vertical Accuracy is consistent with injected value check

If the Geodetic Vertical Accuracy value exposed by the SP API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v22a.NET0260,Table1,16](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the valid injected value.

## ⚠️ Horizontal Accuracy is exposed correctly check

If the Horizontal Accuracy value exposed by the SP API is missing or invalid this check will fail per:
**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** because the SP violates the SP API contract;
**[astm.f3411.v22a.NET0260,Table1,17](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Horizontal Accuracy is consistent with injected value check

If the Horizontal Accuracy value exposed by the SP API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v22a.NET0260,Table1,17](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the valid injected value.

## ⚠️ Speed Accuracy is exposed correctly check

If the Speed Accuracy value exposed by the SP API is missing or invalid this check will fail per:
**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** because the SP violates the SP API contract;
**[astm.f3411.v22a.NET0260,Table1,18](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Speed Accuracy is consistent with injected value check

If the Speed Accuracy value exposed by the SP API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v22a.NET0260,Table1,18](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the valid injected value.

## ⚠️ Track Direction is exposed correctly check

If the Track Direction value exposed by the SP API is missing or invalid this check will fail per:
**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** because the SP violates the SP API contract;
**[astm.f3411.v22a.NET0260,Table1,19](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Track Direction is consistent with injected value check

If the Track Direction value exposed by the SP API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v22a.NET0260,Table1,19](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the valid injected value.

## ⚠️ Speed is exposed correctly check

If the Speed value exposed by the SP API is missing or invalid this check will fail per:
**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** because the SP violates the SP API contract;
**[astm.f3411.v22a.NET0260,Table1,20](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Speed is consistent with injected value check

If the Speed value exposed by the SP API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v22a.NET0260,Table1,20](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the valid injected value.

## ⚠️ Vertical Speed is exposed correctly check

If the Vertical Speed value exposed by the SP API is missing or invalid this check will fail per:
**[astm.f3411.v22a.NET0710,1](../../../../requirements/astm/f3411/v22a.md)** because the SP violates the SP API contract;
**[astm.f3411.v22a.NET0260,Table1,21](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Vertical Speed is consistent with injected value check

If the Vertical Speed value exposed by the SP API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v22a.NET0260,Table1,21](../../../../requirements/astm/f3411/v22a.md)** because the SP fails to expose data consistent with the valid injected value.
