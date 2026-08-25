# InterUSS Authorization Requirements

## Overview

When a test designer requires certain behavior from an authorization source/server, the requirements below are violated when observed behavior differs from expected.

## Requirements

### <tt>AuthType</tt>

The authorization source must be of a particular type.

### <tt>AuthAdapterAttribute</tt>

A particular attribute of the AuthAdapter providing authorization must satisfy the criteria specified.

### <tt>GenerateAccessToken</tt>

When provided with a valid and well-formed request to generate an access token, the provider of an authorization source must ensure that an access token is generated as requested.

### <tt>Signature</tt>

The cryptographic signature of a generated access token JWT must validate against a particular public key.

### <tt>Algorithm</tt>

The algorithm used (per `alg` in header) in a generated access token JWT must be the expected algorithm.

### <tt>HeaderValue</tt>

The value of a particular key in a generated access token JWT header must satisfy specified criteria such as equaling an expected value.

### <tt>DurationLongerThan</tt>

The `exp` claim in a generated access token JWT payload must be at least a specified duration beyond when the access token was requested.

### <tt>DurationShorterThan</tt>

The `exp` claim in a generated access token JWT payload may not be more than a specified duration beyond when the access token was requested.

### <tt>ClaimValue</tt>

The value of a particular claim in a generated access token JWT payload must satisfy specified criteria such as equaling an expected value.
