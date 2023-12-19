# Validate flight sharing invalid data test step fragment

This step verifies that a created flight is shared properly per ASTM F3548-21 by querying the DSS for flights in the area of the flight intent, and then retrieving the details from the USS if the operational intent reference is found.  See `expect_shared_with_invalid_data` in invalid_op_test_steps.py.

## 🛑 DSS responses check

**[astm.f3548.v21.DSS0005](../../../../../requirements/astm/f3548/v21.md)**

## 🛑 Operational intent shared correctly check

If a reference to the operational intent for the flight is not found in the DSS, this check will fail per **[astm.f3548.v21.USS0005](../../../../../requirements/astm/f3548/v21.md)** and **[astm.f3548.v21.OPIN0025](../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Operational intent details retrievable check

If the operational intent details for the flight cannot be retrieved from the USS, this check will fail per **[astm.f3548.v21.USS0105](../../../../../requirements/astm/f3548/v21.md)** and **[astm.f3548.v21.OPIN0025](../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Invalid data in Operational intent details shared by Mock USS for negative test check

**[interuss.mock_uss.hosted_instance.ExposeInterface](../../../../../requirements/interuss/mock_uss/hosted_instance.md)**.

Mock USS shares operational intent details with specified invalid data in response for the negative test case as per
[the GetOperationalIntentDetailsResponse schema of the OpenAPI specification](https://github.com/astm-utm/Protocol/blob/v1.0.0/utm.yaml#L1120).
If the operational intent details from mock_uss does not contain the specified invalid data, this check will fail.
It would mean mock_uss is not behaving correctly.

