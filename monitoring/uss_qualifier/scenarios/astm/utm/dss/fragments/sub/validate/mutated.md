# Validate mutated subscription test step fragment

This test step fragment attempts to validate a single subscription returned by the DSS after its mutation.

The code for these checks lives in the [subscription_validator.py](../../../validators/subscription_validator.py) class.

## ⚠️ Mutated subscription version is updated check

Following a mutation, the DSS needs to update the subscription version, otherwise it is in violation of **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## [Positive index](positive_index.md)
