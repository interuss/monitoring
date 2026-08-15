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

#### Access token retrievable check

If a token cannot be retrieved, the provider of the authorization source fails to meet **interuss.communications.authorization.GenerateAccessToken**.

### Validate access token test step

In this step, the access token retrieved in the previous step is evaluated according to the provided expectations.

#### Token signature validates against public key check

If the cryptographic signature of the access token JWT does not validate against the expected public key, the provider of the authorization source fails to meet **interuss.communications.authorization.Signature**.

