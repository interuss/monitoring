# Validate the content of a constraint reference test step fragment

This test step fragment attempts to validate the content of a single constraint reference returned by the DSS.

The code for these checks lives in the [cr_validator.py](../../../validators/cr_validator.py) class.

## ⚠️ Returned constraint reference ID is correct check

If the returned constraint reference ID does not correspond to the one specified in the creation parameters,
**[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)** is not respected.

## ⚠️ Returned constraint reference has a manager check

If the returned constraint reference has no manager defined, **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)** is not respected.

## ⚠️ Returned constraint reference manager is correct check

The returned manager must correspond to the identity of the client that created the constraint at the DSS,
otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Returned constraint reference has an USS base URL check

If the returned constraint reference has no USS base URL defined, **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)** is not respected.

## ⚠️ Returned constraint reference base URL is correct check

The returned USS base URL must be prefixed with the USS base URL that was provided at constraint reference creation, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Returned constraint reference has a start time check

If the returned constraint reference has no start time defined, **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)** is not respected.

## ⚠️ Returned start time is correct check

The returned start time must be the same as the provided one, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Returned constraint reference has an end time check

Constraint references need a defined end time in order to limit their duration: if the DSS omits to set the end time, it will be in violation of **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Returned end time is correct check

The returned end time must be the same as the provided one, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)**.

## ⚠️ Returned constraint reference has an OVN check

If the returned constraint reference has no OVN defined, **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)** is not respected.

## ⚠️ Returned constraint reference has a version check

If the returned constraint reference has no version defined, **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)** is not respected.
