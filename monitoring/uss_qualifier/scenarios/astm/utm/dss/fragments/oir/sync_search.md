# Verify operational intent reference synchronization through search test step fragment

This test step fragment validates that operational intent references are properly synchronized across a set of DSS instances
by searching for an operational intent reference that is known to exist in a specific area at each one of the DSS instances.

## 🛑 Propagated operational intent reference general area is synchronized check

When querying a secondary DSS for operational intents in the planning area that contains the propagated operational
intent, if the propagated operational intent is not contained in the response, then the general area in which the
propagated operational intent is located is not synchronized across DSS instances.
As such, either the primary or the secondary DSS fails to properly implement one of the following requirements:

**[astm.f3548.v21.DSS0210,2e](../../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.

## [Operational Intent Reference fields are synchronized](./sync_fields.md)
