# Monitoring library

This directory contains libraries supporting by multiple monitoring tools.

## Auth specs
Many monitoring tools require information describing how to obtain access
tokens.  This information is provided via an "auth spec", which is a string,
usually specified on the command line.  Each auth spec takes the form of
`AuthAdapter(value1,value2,...)`.  The `AuthAdapter` portion is the name of an
AuthAdapter subclass defined in [auth.py](../monitorlib/auth.py) (for example:
`UsernamePassword`, `ServiceAccount`, `DummyOAuth`, or `SignedRequest`).  The
`value1,value2,...` parameters are those accepted by the particular
AuthAdapter's `__init__` constructor.  Both ordinal (e.g.,
`AuthAdapter(value1,value2)`) and keyword (e.g.,
`AuthAdapter(param1=value1,param2=value2)`) parameters are accepted.  Notes:

1. The spec must be a singular shell string unbroken by spaces and so should
   probably be wrapped in quotes on the command line.
1. All parameter types are strings.
1. String values are not delimited by any quote-like characters.

### Examples

* `NoAuth()`
* `UsernamePassword(https://example.interuss.org/token, username=uss1, password=uss1,
   client_id=uss1)`
* `ServiceAccount(https://example.interuss.org/token, ~/credentials/account.json)`
* `FlightPassport(https://example.interuss.org/oauth/token/, client_id=NdepxcA, client_secret=PSh7DzZdN)`
* `DummyOAuth(http://localhost:8085/token, sub=fake_uss)`
* `SignedRequest(https://example.interuss.org/oauth/token, client_id=uss1.com,
   key_path=/auth/uss1.key, cert_url=https://uss1.com/uss1.der)`
* `ClientIdClientSecret(https://example.interuss.org/token, uss1, dXNzMQ==)`
* `PrivateKeyJWT(https://example.interuss.org/token, uss1, key_path=/auth/uss1.key)`
* `PrivateKeyJWT(https://example.interuss.org/token, uss1, key=LS0tLS1CRUdJTi<...>, key_id=uss1)`

### Testing

Use [`get_access_token.py`](../get_access_token.py) to retrieve an access token
using a provided auth spec.

## Test resource IDs

[ids.py](ids.py) provides `register_resource_type` and `IDFactory` for creating
recognizable UUIDv4-format test IDs.  Register each resource type with a code
that is unique across all monitoring tools.  The comment above
`register_resource_type` identifies the next available code; update it after
allocating codes.  `IDFactory` encodes the owner, resource type code, and an
instance index from 0 to 255.  The default index of 0 preserves legacy IDs.

If a test resource (subscription, operational intent, etc.) is orphaned in a DSS,
use [decode_id.py](decode_id.py) to identify its owner and origin.  From the
repository root, run:

```shell
uv run python -m monitoring.monitorlib.decode_id <ID>
```
