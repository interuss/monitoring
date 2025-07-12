# Validate subscription fields test step fragment

This test step fragment attempts to validate a single subscription returned by the DSS after its mutation.

The code for these checks lives in the [subscription_validator.py](../../../validators/subscription_validator.py) class.

## ⚠️ New subscription has a notification index of 0 check

The notification index of a newly created subscription must be 0, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.
