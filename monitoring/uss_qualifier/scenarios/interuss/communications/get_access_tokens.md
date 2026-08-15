# Get access tokens test scenario

## Overview

This scenario obtains one or more access tokens using an auth adapter and, optionally, validates certain characteristics of the tokens obtained.

## Resources

### auth_adapter

An [`AuthAdapterResources`](../../../resources/communications/auth_adapter.py) used to get the access tokens

### expectations

An [`AccessTokensExpectationsResource`](../../../resources/communications/access_tokens_expectations.py) describing what is expected of the access tokens acquired

## Validate access tokens test case

### Get access token test step

In this step, an access token is retrieved using the provided auth adapter.

#### ⚠️ Access token retrievable check

If a token cannot be retrieved, the provider of the authorization source fails to meet **[interuss.communications.authorization.GenerateAccessToken](../../../requirements/interuss/communications/authorization.md)**.

### Validate access token test step

In this step, the access token retrieved in the previous step is evaluated according to the provided expectations.

#### ⚠️ Token header algorithm check

If the JWT header `alg` claim does not equal the expected algorithm, the provider of the authorization source fails to meet **[interuss.communications.authorization.Algorithm](../../../requirements/interuss/communications/authorization.md)**.

#### ⚠️ Token header value check

If a specified key in the JWT header does not satisfy the defined criteria (such as matching an expected string or number), the provider of the authorization source fails to meet **[interuss.communications.authorization.HeaderValue](../../../requirements/interuss/communications/authorization.md)**.

#### ⚠️ Token signature validates against public key check

If the cryptographic signature of the access token JWT does not validate against the expected public key, the provider of the authorization source fails to meet **[interuss.communications.authorization.Signature](../../../requirements/interuss/communications/authorization.md)**.

#### ⚠️ Token expiration duration longer than check

If the access token expiration time (`exp` claim) is not at least the specified duration beyond the token request timestamp, the provider of the authorization source fails to meet **[interuss.communications.authorization.DurationLongerThan](../../../requirements/interuss/communications/authorization.md)**.

#### ⚠️ Token expiration duration shorter than check

If the access token expiration time (`exp` claim) is further in the future than the token request timestamp plus the specified duration limit, the provider of the authorization source fails to meet **[interuss.communications.authorization.DurationShorterThan](../../../requirements/interuss/communications/authorization.md)**.

#### ⚠️ Token payload claim value check

If a specified claim in the JWT payload does not satisfy the defined criteria (such as matching an expected string or number), the provider of the authorization source fails to meet **[interuss.communications.authorization.ClaimValue](../../../requirements/interuss/communications/authorization.md)**.

