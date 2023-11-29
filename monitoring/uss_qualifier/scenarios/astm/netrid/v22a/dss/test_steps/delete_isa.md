# Delete ISA test step

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
