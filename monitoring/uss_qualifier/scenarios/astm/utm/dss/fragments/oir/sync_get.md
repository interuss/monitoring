# Verify operational intent reference synchronization through direct access test step fragment

This test step fragment validates that operational intent references are properly synchronized across a set of DSS instances
by querying an operational intent reference that is known to exist at each one of the DSS instances.

## 🛑 Operational intent reference can be found at every DSS check

If the previously created or mutated operational intent reference cannot be found at a DSS, either one of the instances at which the operational intent reference was created or the one that was queried,
is failing to implement one of the following requirements:

**[astm.f3548.v21.DSS0210,2a](../../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.

## [Operational Intent Reference fields are synchronized](./sync_fields.md)
