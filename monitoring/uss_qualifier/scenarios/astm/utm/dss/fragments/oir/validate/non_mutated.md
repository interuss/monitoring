# Validate non-mutated operational intent reference test step fragment

This test step fragment attempts to validate a single operational intent reference returned by the DSS,
usually after it has been created or to confirm it has not been mutated by an action.

The code for these checks lives in the [oir_validator.py](../../../validators/oir_validator.py) class.

## ⚠️ Non-mutated operational intent reference keeps the same version check

If the version of the operational intent reference is updated without there having been any mutation of the operational intent reference, the DSS is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Non-mutated operational intent reference keeps the same OVN check

If the OVN of the operational intent reference is updated without there having been any mutation of the operational intent reference, the DSS is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**.
