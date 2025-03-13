# Create ISA test step fragment

This page describes the content of a common test step where a mutation of an ISA should be successful.
See `DSSWrapper.put_isa` in [`dss_wrapper.py`](../../../dss_wrapper.py).

## [Put ISA](put_isa.md)

Checks common to creation and mutation.

## ⚠️ ISA version changed check

When the ISA is updated, the DSS returns the updated version of the ISA in the response body.  If this version remains the same as the one before the update, **[astm.f3411.v22a.DSS0030,a](../../../../../../requirements/astm/f3411/v22a.md)** was not implemented correctly and this check will fail.
