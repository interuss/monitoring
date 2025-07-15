# Validate subscription notification index is equal to 0 test step fragment

This test step fragment attempts to validate a single subscription's notification index returned by the DSS after the creation
of a subscription.

The index may change for reasons outside of `uss_qualifier`'s control or awareness, therefore the only thing we can reliably verify with regard to the notification index is that:
 - it should be there
 - on creation of the entity it should be 0
 - after creation, it should be 0 or greater

The code for these checks lives in the [subscription_validator.py](../../../validators/subscription_validator.py) class.

## ⚠️ New subscription has a notification index of 0 check

The notification index of a newly created subscription must be 0, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.
