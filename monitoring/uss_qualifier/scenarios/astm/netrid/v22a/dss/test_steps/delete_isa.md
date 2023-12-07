# Delete ISA test step fragment

This page describes the content of a common test step where a deletion of an ISA should be successful.
See `DSSWrapper.del_isa` in [`dss_wrapper.py`](../../../dss_wrapper.py).

## ISA response format check

The API for **[astm.f3411.v22a.DSS0030,b](../../../../../../requirements/astm/f3411/v22a.md)** specifies an explicit format that the DSS responses must follow.  If the DSS response does not validate against this format, this check will fail.

## ISA ID matches check

When the ISA is deleted, the DSS returns the ID of the ISA in the response body.  If this ID does not match the ID in the resource path, **[astm.f3411.v22a.DSS0030,b](../../../../../../requirements/astm/f3411/v22a.md)** was not implemented correctly and this check will fail.

## ISA version format check

Because the ISA version must be used in URLs, it must be URL-safe even though the ASTM standards do not explicitly require this.  If the indicated ISA version is not URL-safe, this check will fail.

## ISA version matches check

When the ISA is deleted, the DSS returns the version of the ISA in the response body.  If this version does not match the version in the resource path, **[astm.f3411.v22a.DSS0030,b](../../../../../../requirements/astm/f3411/v22a.md)** was not implemented correctly and this check will fail.

## ISA start time matches check

If a start time between slightly before now and an arbitrary time in the future was specified, and the DSS response indicates an ISA start time different from this value, **[astm.f3411.v22a.DSS0030,a](../../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

## ISA end time matches check

The ISA creation request specified an exact end time, so the DSS should have created an ISA ending at exactly that time. If the DSS response indicates the ISA end time is not this value, **[astm.f3411.v22a.DSS0030,a](../../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

## ISA URL matches check

When the ISA is created, the DSS returns the URL of the ISA in the response body. If this URL does not match the URL requested, **[astm.f3411.v22a.DSS0030,a](../../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.
