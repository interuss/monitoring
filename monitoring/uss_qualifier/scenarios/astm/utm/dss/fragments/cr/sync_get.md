# Verify constraint reference synchronization through direct access test step fragment

This test step fragment validates that constraint references are properly synchronized across a set of DSS instances
by querying a constraint reference that is known to exist at each one of the DSS instances.

## 🛑 Constraint reference can be found at every DSS check

If the previously created or mutated constraint reference cannot be found at a DSS, either one of the instances at which the constraint reference was created or the one that was queried,
is failing to implement one of the following requirements:

**[astm.f3548.v21.DSS0210,2a](../../../../../../requirements/astm/f3548/v21.md)**, if the API is not working as described by the OpenAPI specification;
**[astm.f3548.v21.DSS0215](../../../../../../requirements/astm/f3548/v21.md)**, if the DSS is returning API calls to the client before having updated its underlying distributed storage.

As a result, the DSS pool under test is failing to meet **[astm.f3548.v21.DSS0020](../../../../../../requirements/astm/f3548/v21.md)**.

## [Constraint Reference fields are synchronized](./sync_fields.md)
