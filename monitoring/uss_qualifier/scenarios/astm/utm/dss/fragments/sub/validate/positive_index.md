# Validate subscription fields test step fragment

This test step fragment attempts to validate a single subscription returned by the DSS after its mutation.

The code for these checks lives in the [subscription_validator.py](../../../validators/subscription_validator.py) class.

## ⚠️ Returned notification index is equal to or greater than 0 check

If the notification index of the subscription is less than 0, the DSS fails to properly implement **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.
