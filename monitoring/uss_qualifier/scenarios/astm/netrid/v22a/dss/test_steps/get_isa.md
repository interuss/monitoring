# Get ISA test step fragment

This page describes the content of a common test step where a request for an ISA by its ID should be successful.
See `ISAValidator` in [`isa_validator.py`](../../../common/dss/isa_validator.py).

## ISA response format check

While F3411-22a does not explicitly require the implementation of the ISA search endpoint, Annex A4 specifies the explicit format for this endpoint.  If this format is not followed, this check will fail per **[interuss.f3411.dss_endpoints.GetISA](../../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

## ISA ID matches check

The DSS returns the ID of the ISA in the response body. If this ID does not match the ID in the resource path, **[interuss.f3411.dss_endpoints.GetISA](../../../../../../requirements/interuss/f3411/dss_endpoints.md)** was not implemented correctly and this check will fail.

## ISA version format check

Because the ISA version must be used in URLs, it must be URL-safe even though the ASTM standards do not explicitly require this. If the indicated ISA version is not URL-safe, this check will fail.

## ISA version matches check

The DSS returns the version of the ISA in the response body. If this version does not match the version that was returned after creation, and that no modification of the ISA occurred in the meantime, **[interuss.f3411.dss_endpoints.GetISA](../../../../../../requirements/interuss/f3411/dss_endpoints.md)** was not implemented correctly and this check will fail.

## ISA start time matches check

The ISA creation request specified an exact start time slightly past now, so the DSS should have created an ISA starting at exactly that time. If the DSS response indicates the ISA start time is not this value, **[astm.f3411.v22a.DSS0030,a](../../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

## ISA end time matches check

The ISA creation request specified an exact end time, so the DSS should have created an ISA ending at exactly that time. If the DSS response indicates the ISA end time is not this value, **[astm.f3411.v22a.DSS0030,a](../../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.

## ISA URL matches check

When the ISA is created, the DSS returns the URL of the ISA in the response body. If this URL does not match the URL requested, **[astm.f3411.v22a.DSS0030,a](../../../../../../requirements/astm/f3411/v22a.md)** is not implemented correctly and this check will fail.
