# Get access tokens test scenario

## Overview

This scenario obtains one or more access tokens using an auth adapter and, optionally, validates certain characteristics of the tokens obtained.

## Resources

### auth_adapter

An [`AuthAdapterResource`](../../../resources/communications/auth_adapter.py) used to get the access tokens

### token_expectations

An [`AccessTokensExpectationsResource`](../../../resources/communications/access_token_expectations.py) describing what is expected of the access tokens acquired

### adapter_expectations

An [`AuthAdapterExpectationsResource`](../../../resources/communications/auth_adapter.py) describing what is expected of the auth adapter used to acquire access tokens

## Validate auth adapter test case

### Validate auth adapter characteristics test step

In this step, the characteristics of the auth_adapter resource supplied to this scenario are evaluated according to adapter_expectations.

#### ⚠️ Auth adapter type check

If the auth_adapter resource contains an auth adapter that differs from the type specified in adapter_expectations, the provider of the authorization source fails to meet **[interuss.communications.authorization.AuthType](../../../requirements/interuss/communications/authorization.md)**.

#### ⚠️ Auth adapter attribute check

If the auth_adapter resource contains an auth adapter with an attribute that does not match a criterion specified in adapter_expectations, the provider of the authorization source fails to meet **[interuss.communications.authorization.AuthAdapterAttribute](../../../requirements/interuss/communications/authorization.md)**.

## Validate access tokens test case

### Get access token test step

In this step, an access token is retrieved using the provided auth adapter.

#### ⚠️ Access token retrievable check

If a token cannot be retrieved, the provider of the authorization source fails to meet **[interuss.communications.authorization.GenerateAccessToken](../../../requirements/interuss/communications/authorization.md)**.

### Validate access token test step

In this step, the access token retrieved in the previous step is evaluated according to the provided expectations.

#### ⚠️ Token header value check

If a specified key in the JWT header does not satisfy the defined criteria (such as matching an expected string or number), the provider of the authorization source fails to meet **[interuss.communications.authorization.HeaderValue](../../../requirements/interuss/communications/authorization.md)**.

#### ⚠️ Token signature validates against public key check

If the cryptographic signature of the access token JWT does not validate against the expected public key, the provider of the authorization source fails to meet **[interuss.communications.authorization.Signature](../../../requirements/interuss/communications/authorization.md)**.

#### ⚠️ Token payload claim value check

If a specified claim in the JWT payload does not satisfy the defined criteria (such as matching an expected string or number), the provider of the authorization source fails to meet **[interuss.communications.authorization.ClaimValue](../../../requirements/interuss/communications/authorization.md)**.

