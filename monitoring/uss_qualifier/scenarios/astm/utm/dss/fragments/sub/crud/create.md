# Create subscription test step fragment

This test step fragment validates that subscriptions can be created.

## [Verify query succeeds](./create_query.md)

## 🛑 Create subscription response format conforms to spec check

The response to a successful subscription creation query is expected to conform to the format defined by the OpenAPI specification under the `A3.1` Annex of ASTM F3548−21.

If it does not, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## 🛑 Create subscription response content is correct check

A successful subscription creation query is expected to return a well-defined body, the content of which reflects the created subscription.

If the content of the response does not correspond to the requested content, the DSS is failing to implement **[astm.f3548.v21.DSS0005,5](../../../../../../../requirements/astm/f3548/v21.md)**.

## [Validate subscription fields](../validate/correctness.md)

## [Validate notification index](../validate/zero_index.md)
