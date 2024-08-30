# Delete constraint reference test step fragment

This test step fragment validates that constraint references can be deleted

## 🛑 Delete constraint reference query succeeds check

A query to delete a constraint reference, by its owner and when the correct OVN is provided, should succeed, otherwise the DSS is in violation of **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)**.

## [Response format](./delete_format.md)

Check response format

## 🛑 Delete constraint reference response content is correct check

A successful constraint reference deletion query is expected to return a body, the content of which reflects the constraint reference at the moment of deletion.
If the content of the response does not correspond to what was requested, the DSS is failing to implement **[astm.f3548.v21.DSS0005,3](../../../../../../../requirements/astm/f3548/v21.md)**.

This check will usually be performing a series of sub-checks from the [validate](../validate) fragments.
