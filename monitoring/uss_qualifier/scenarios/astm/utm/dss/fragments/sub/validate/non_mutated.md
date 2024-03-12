# Validate non-mutated subscription test step fragment

This test step fragment attempts to validate a single subscription returned by the DSS after its creation or mutation.

The code for these checks lives in the [subscription_validator.py](../../../validators/subscription_validator.py) class.

## ⚠️ Non-mutated subscription keeps the same version check

If the version of the subscription is updated without there having been any mutation of the subscription, the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.
