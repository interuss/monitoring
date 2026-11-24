"""Unauthenticated token generation for local development and testing."""

import os
import time
from pathlib import Path

from flask import Flask, jsonify, request
from jwcrypto import jwk, jwt


def create_app(private_key_file: str | None = None) -> Flask:
    key = jwk.JWK.from_pem(
        Path(
            private_key_file
            or os.environ.get(
                "DUMMY_OAUTH_PRIVATE_KEY_FILE", "/var/test-certs/auth2.key"
            )
        ).read_bytes()
    )
    if key["kty"] != "RSA" or not key.has_private:
        raise ValueError("Dummy OAuth requires an RSA private key")
    key_id = key.thumbprint()
    public_key = key.export_public(as_dict=True)
    public_key.update(kid=key_id, alg="RS256", use="sig")

    webapp = Flask(__name__)

    @webapp.get("/token")
    def get_token():
        for name in ("intended_audience", "scope"):
            if name not in request.args:
                return jsonify(message=f"Missing `{name}` query parameter"), 400
        try:
            expires = int(request.args.get("expire", int(time.time()) + 3600))
        except ValueError:
            return jsonify(
                message="Invalid `expire` query parameter: expected integer"
            ), 400

        token = jwt.JWT(
            header={"typ": "JWT", "alg": "RS256", "kid": key_id},
            claims={
                "aud": request.args["intended_audience"],
                "scope": request.args["scope"],
                "iss": request.args.get("issuer", "dummyoauth"),
                "exp": expires,
                "sub": request.args.get("sub", "fake_uss"),
            },
        )
        token.make_signed_token(key)
        return jsonify(access_token=token.serialize())

    @webapp.get("/.well-known/jwks.json")
    def get_jwks():
        return jsonify(keys=[public_key])

    return webapp
