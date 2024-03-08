# Validate mutated operational intent reference test step fragment

This test step fragment attempts to validate a single operational intent reference returned by the DSS,
usually after it has been mutated.

The code for these checks lives in the [oir_validator.py](../../../validators/oir_validator.py) class.

## ⚠️ Mutated operational intent reference version is updated check

Following a mutation, the DSS needs to update the operational intent reference version, otherwise it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Mutated operational intent reference OVN is updated check

Following a mutation, the DSS needs to update the operational intent reference OVN, otherwise it is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**.
