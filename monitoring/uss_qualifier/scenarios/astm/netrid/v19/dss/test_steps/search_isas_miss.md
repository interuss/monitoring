# Search ISAs Miss test step fragment

This page describes the content of a common test step where a search for ISAs should be successful, but the ISAs
relevant to the current scenario are not expected to be present.

See `DSSWrapper.search_isa` in [`dss_wrapper.py`](../../../dss_wrapper.py).

## ISAs search response format check

While F3411-19 does not explicitly require the implementation of the ISA search endpoint, Annex A4 specifies the explicit format for this endpoint.  If this format is not followed, this check will fail per **[interuss.f3411.dss_endpoints.SearchISAs](../../../../../../requirements/interuss/f3411/dss_endpoints.md)**.

## ISA version format check

Because the ISA version must be used in URLs, it must be URL-safe even though the ASTM standards do not explicitly require this. If the indicated ISA version is not URL-safe, this check will fail.
