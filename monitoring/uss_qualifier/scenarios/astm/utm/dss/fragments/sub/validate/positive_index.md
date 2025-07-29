# Validate subscription notification index is positive test step fragment

This test step fragment attempts to validate a single subscription's notification index returned by the DSS after a mutation,
or for any query returning a subscription except for its initial creation.

The index may change for reasons outside of `uss_qualifier`'s control or awareness, therefore the only thing we can reliably verify with regard to the notification index is that:
 - it should be there
 - on creation of the entity it should be 0
 - after creation, it should be 0 or greater

The code for these checks lives in the [subscription_validator.py](../../../validators/subscription_validator.py) class.

## ⚠️ Returned notification index is equal to or greater than 0 check

If the notification index of the subscription is less than 0, the DSS fails to properly implement **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

