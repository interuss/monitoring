# Validate non-mutated constraint reference test step fragment

This test step fragment attempts to validate a single constraint reference returned by the DSS,
usually after it has been created or to confirm it has not been mutated by an action.

The code for these checks lives in the [cr_validator.py](../../../validators/cr_validator.py) class.

## ⚠️ Non-mutated constraint reference keeps the same version check

If the version of the constraint reference is updated without there having been any mutation of the constraint reference, the DSS is in violation of **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Non-mutated constraint reference keeps the same OVN check

If the OVN of the constraint reference is updated without there having been any mutation of the constraint reference, the DSS is in violation of **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)**.
