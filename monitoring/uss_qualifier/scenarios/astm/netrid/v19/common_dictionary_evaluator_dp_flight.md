# ASTM NetRID v19 Display Provider flight consistency with Common Data Dictionary test step fragment

This fragment is implemented in `common_dictionary_evaluator.py:RIDCommonDictionaryEvaluator.evaluate_dp_flight`.

## ⚠️ UAS ID (Serial number) is exposed correctly check

If the UAS ID's serial number value exposed by the observation API is valid this check will succeed per
**[astm.f3411.v19.NET0470,Table1,1](../../../../requirements/astm/f3411/v19.md)** and **[astm.f3411.v19.NET0470,Table1,1a](../../../../requirements/astm/f3411/v19.md)** since the DP exposes data consistent with the Common Data Dictionary.

## ⚠️ UAS ID (Serial number) is consistent with injected value check

If the UAS ID's serial number value exposed by the observation API is consistent with the injected value this check will succeed per
**[astm.f3411.v19.NET0470,Table1,1](../../../../requirements/astm/f3411/v19.md)** and **[astm.f3411.v19.NET0470,Table1,1a](../../../../requirements/astm/f3411/v19.md)** since the DP exposes data consistent with the valid injected value.

## ⚠️ UAS ID (Registration ID) is exposed correctly check

If the UAS ID's registration ID value exposed by the observation API is valid this check will succeed per
**[astm.f3411.v19.NET0470,Table1,1](../../../../requirements/astm/f3411/v19.md)** and **[astm.f3411.v19.NET0470,Table1,1b](../../../../requirements/astm/f3411/v19.md)** since the DP exposes data consistent with the Common Data Dictionary.

## ⚠️ UAS ID (Registration ID) is consistent with injected value check

If the UAS ID's registration ID value exposed by the observation API is consistent with the injected value this check will succeed per
**[astm.f3411.v19.NET0470,Table1,1](../../../../requirements/astm/f3411/v19.md)** and **[astm.f3411.v19.NET0470,Table1,1b](../../../../requirements/astm/f3411/v19.md)** since the DP exposes data consistent with the valid injected value.

## ⚠️ UA type is exposed correctly check

If the UA type value exposed by the observation API is invalid this check will fail per:
**[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)** because the DP violates the observation API contract;
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,3](../../../../requirements/astm/f3411/v19.md)** because the DP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ UA type is consistent with injected value check

If the UA type value exposed by the observer API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,3](../../../../requirements/astm/f3411/v19.md)**  because the DP fails to expose data consistent with the valid injected value.

## ⚠️ Timestamp is exposed correctly check

If the Timestamp value exposed by the observation API is invalid this check will fail per:
**[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)** because the DP violates the observation API contract;
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,4](../../../../requirements/astm/f3411/v19.md)** because the DP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Timestamp is consistent with injected value check

If the Timestamp value exposed by the observer API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,4](../../../../requirements/astm/f3411/v19.md)**  because the DP fails to expose data consistent with the valid injected value.

## ⚠️ Timestamp accuracy is exposed correctly check

If the Timestamp accuracy value exposed by the observation API is invalid this check will fail per:
**[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)** because the DP violates the observation API contract;
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,5](../../../../requirements/astm/f3411/v19.md)** because the DP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Timestamp accuracy is consistent with injected value check

If the Timestamp accuracy value exposed by the observer API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,5](../../../../requirements/astm/f3411/v19.md)**  because the DP fails to expose data consistent with the valid injected value.

## ⚠️ Operational status is exposed correctly check

If the Operational status value exposed by the observation API is invalid this check will fail per:
**[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)** because the DP violates the observation API contract;
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,6](../../../../requirements/astm/f3411/v19.md)** because the DP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Operational status is consistent with injected value check

If the Operational status value exposed by the observer API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,6](../../../../requirements/astm/f3411/v19.md)**  because the DP fails to expose data consistent with the valid injected value.

## ⚠️ Geodetic Altitude is exposed correctly check

If the Geodetic Altitude value exposed by the observation API is invalid this check will fail per:
**[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)** because the DP violates the observation API contract;
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,11](../../../../requirements/astm/f3411/v19.md)** because the DP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Geodetic Altitude is consistent with injected value check

If the Geodetic Altitude value exposed by the observer API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,11](../../../../requirements/astm/f3411/v19.md)**  because the DP fails to expose data consistent with the valid injected value.

## ⚠️ Height is exposed correctly check

If the Height value exposed by the observation API is invalid this check will fail per:
**[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)** because the DP violates the observation API contract;
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,13](../../../../requirements/astm/f3411/v19.md)** because the DP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Height is consistent with injected value check

If the Height value exposed by the observer API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,13](../../../../requirements/astm/f3411/v19.md)**  because the DP fails to expose data consistent with the valid injected value.

## ⚠️ Height type is exposed correctly check

If the Height type value exposed by the observation API is invalid this check will fail per:
**[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)** because the DP violates the observation API contract;
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,14](../../../../requirements/astm/f3411/v19.md)** because the DP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Height type is consistent with injected value check

If the Height type value exposed by the observer API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,14](../../../../requirements/astm/f3411/v19.md)**  because the DP fails to expose data consistent with the valid injected value.

## ⚠️ Geodetic Vertical Accuracy is exposed correctly check

If the Geodetic Vertical Accuracy value exposed by the observation API is invalid this check will fail per:
**[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)** because the DP violates the observation API contract;
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,15](../../../../requirements/astm/f3411/v19.md)** because the DP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Geodetic Vertical Accuracy is consistent with injected value check

If the Geodetic Vertical Accuracy value exposed by the observer API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,15](../../../../requirements/astm/f3411/v19.md)**  because the DP fails to expose data consistent with the valid injected value.

## ⚠️ Horizontal Accuracy is exposed correctly check

If the Horizontal Accuracy value exposed by the observation API is invalid this check will fail per:
**[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)** because the DP violates the observation API contract;
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,16](../../../../requirements/astm/f3411/v19.md)** because the DP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Horizontal Accuracy is consistent with injected value check

If the Horizontal Accuracy value exposed by the observer API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,16](../../../../requirements/astm/f3411/v19.md)**  because the DP fails to expose data consistent with the valid injected value.

## ⚠️ Speed Accuracy is exposed correctly check

If the Speed Accuracy value exposed by the observation API is invalid this check will fail per:
**[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)** because the DP violates the observation API contract;
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,17](../../../../requirements/astm/f3411/v19.md)** because the DP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Speed Accuracy is consistent with injected value check

If the Speed Accuracy value exposed by the observer API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,17](../../../../requirements/astm/f3411/v19.md)**  because the DP fails to expose data consistent with the valid injected value.

## ⚠️ Track Direction is exposed correctly check

If the Track Direction value exposed by the observation API is invalid this check will fail per:
**[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)** because the DP violates the observation API contract;
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,18](../../../../requirements/astm/f3411/v19.md)** because the DP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Track Direction is consistent with injected value check

If the Track Direction value exposed by the observer API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,18](../../../../requirements/astm/f3411/v19.md)**  because the DP fails to expose data consistent with the valid injected value.

## ⚠️ Speed is exposed correctly check

If the Speed value exposed by the observation API is invalid this check will fail per:
**[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)** because the DP violates the observation API contract;
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,19](../../../../requirements/astm/f3411/v19.md)** because the DP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Speed is consistent with injected value check

If the Speed value exposed by the observer API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,19](../../../../requirements/astm/f3411/v19.md)**  because the DP fails to expose data consistent with the valid injected value.

## ⚠️ Vertical Speed is exposed correctly check

If the Vertical Speed value exposed by the observation API is invalid this check will fail per:
**[interuss.automated_testing.rid.observation.ObservationSuccess](../../../../requirements/interuss/automated_testing/rid/observation.md)** because the DP violates the observation API contract;
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,20](../../../../requirements/astm/f3411/v19.md)** because the DP fails to expose data consistent with the Common Data Dictionary.

## ⚠️ Vertical Speed is consistent with injected value check

If the Vertical Speed value exposed by the observer API is inconsistent with the injected value this check will fail per:
**[astm.f3411.v19.NET0450](../../../../requirements/astm/f3411/v19.md)** because the DP fails to provide accurate data;
**[astm.f3411.v19.NET0470,Table1,20](../../../../requirements/astm/f3411/v19.md)**  because the DP fails to expose data consistent with the valid injected value.
