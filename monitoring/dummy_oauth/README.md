# Dummy OAuth

A development utility that issues RS256 access tokens with arbitrary claims and
publishes their public key as JWKS. It performs no authentication or authorization;
use it only in test environments.

From the repository root, build and run the monitoring image:

```bash
make image
docker run --rm -p 8085:8085 interuss/monitoring \
  sh /app/monitoring/dummy_oauth/start.sh
```

Request a token or retrieve the public key:

```bash
curl 'http://localhost:8085/token?intended_audience=uss.example.com&scope=scope1%20scope2&sub=uss1'
curl 'http://localhost:8085/.well-known/jwks.json'
```

`GET /token` returns `{"access_token": "<JWT>"}`. `intended_audience` and `scope`
are required query parameters. Optional parameters are `issuer` (default
`dummyoauth`), `sub` (default `fake_uss`), and `expire` (an integer Unix timestamp,
default one hour from now). Explicit expiry times may be in the past for testing.
The [OpenAPI interface](../../interfaces/dummy-oauth/dummy-oauth.yaml) describes
both endpoints. Tokens include a `kid` matching the SHA-256 JWK thumbprint in JWKS.

The image includes the existing development key pair at
`/var/test-certs/auth2.key` and `/var/test-certs/auth2.pem`, matching the DSS
dummy-oauth image. Services trusting that public key can verify these tokens.
Set `DUMMY_OAUTH_PRIVATE_KEY_FILE` and mount an RSA private key to use a different
signing key. `DUMMY_OAUTH_PORT` overrides the listening port (default 8085);
adjust the Docker port mapping accordingly. Additional arguments to `start.sh`
are passed to Gunicorn, for example `--workers 2`.
