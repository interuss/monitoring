# Validate the content of an operational intent reference test step fragment

This test step fragment attempts to validate the content of a single operational intent reference returned by the DSS.

Fields that require different handling based on if the operational intent reference was mutated or not are covered

The code for these checks lives in the [oir_validator.py](../../../validators/oir_validator.py) class.

## ⚠️ Returned operational intent reference ID is correct check

If the returned operational intent reference ID does not correspond to the one specified in the creation parameters,
**[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)** is not respected.

## ⚠️ Returned operational intent reference has a manager check

If the returned operational intent reference has no manager defined, **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)** is not respected.

## ⚠️ Returned operational intent reference manager is correct check

The returned manager must correspond to the identity of the client that created the operational intent at the DSS,
otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Returned operational intent reference state is correct check

The returned state must be the same as the provided one, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Returned operational intent reference has an USS base URL check

If the returned operational intent reference has no USS base URL defined, **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)** is not respected.

## ⚠️ Returned operational intent reference base URL is correct check

The returned USS base URL must be prefixed with the USS base URL that was provided at operational intent reference creation, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Returned operational intent reference has a start time check

If the returned operational intent reference has no start time defined, **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)** is not respected.

## ⚠️ Returned start time is correct check

The returned start time must be the same as the provided one, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Returned operational intent reference has an end time check

Operational intent references need a defined end time in order to limit their duration: if the DSS omits to set the end time, it will be in violation of **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Returned end time is correct check

The returned end time must be the same as the provided one, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Returned operational intent reference has a version check

If the returned operational intent reference has no version defined, **[astm.f3548.v21.DSS0005,1](../../../../../../../requirements/astm/f3548/v21.md)** is not respected.
