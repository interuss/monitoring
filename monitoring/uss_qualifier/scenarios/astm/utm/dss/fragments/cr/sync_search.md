# Verify constraint reference synchronization through search test step fragment

This test step fragment validates that constraint references are properly synchronized across a set of DSS instances by
searching for a constraint reference that is known to exist in a specific area at each one of the DSS instances.

## 🛑 Propagated constraint reference general area is synchronized check

When querying a secondary DSS for constraints in the planning area that contains the propagated
constraint, if the propagated constraint is not contained in the response, then the general area in which the
propagated constraint is located is not synchronized across DSS instances.
As such, either the primary or the secondary DSS fail to properly one of the following requirements:

**[astm.f3548.v21.DSS0210,2e](../../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.

## [Constraint Reference fields are synchronized](./sync_fields.md)
