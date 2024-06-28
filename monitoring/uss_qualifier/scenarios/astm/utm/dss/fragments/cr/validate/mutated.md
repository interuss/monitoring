# Validate mutated constraint reference test step fragment

This test step fragment attempts to validate a single constraint reference returned by the DSS,
usually after it has been mutated.

The code for these checks lives in the [cr_validator.py](../../../validators/cr_validator.py) class.

## ⚠️ Mutated constraint reference version is updated check

Following a mutation, the DSS needs to update the constraint reference version, otherwise it is in violation of **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Mutated constraint reference OVN is updated check

Following a mutation, the DSS needs to update the constraint reference OVN, otherwise it is in violation of **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)**.
