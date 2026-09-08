import base64
import json
import os
from unittest import mock

import jwcrypto.jwk
import jwcrypto.jwt
import pytest

from monitoring.monitorlib import auth

_KEY_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "build", "test-certs", "auth2.key"
)
with open(_KEY_PATH, "rb") as f:
    _KEY = jwcrypto.jwk.JWK.from_pem(f.read())


class _Response:
    def __init__(self, status_code: int, content: bytes):
        self.status_code = status_code
        self.content = content

    def json(self):
        return json.loads(self.content.decode("utf-8"))


def test_jwt_bearer_key_from_pem_file():
    adapter = auth.PrivateKeyJWT("http://host/token", "cli", key_path=_KEY_PATH)
    assert adapter._alg == "RS256"
    assert adapter._kid is None


def test_jwt_bearer_key_from_jwk():
    adapter = auth.PrivateKeyJWT(
        "http://host/token",
        "cli",
        key=base64.b64encode(_KEY.export(private_key=True).encode("utf-8")).decode(
            "utf-8"
        ),
        key_id="k1",
    )
    assert adapter._alg == "RS256"
    assert adapter._kid == "k1"


def test_jwt_bearer_missing_or_duplicate_key():
    with pytest.raises(ValueError):
        auth.PrivateKeyJWT("http://host/token", "cli")
    with pytest.raises(ValueError):
        auth.PrivateKeyJWT("http://host/token", "cli", key_path=_KEY_PATH, key="{}")


def test_jwt_bearer_issue_token():
    adapter = auth.PrivateKeyJWT("http://host/token", "cli", key_path=_KEY_PATH)
    with mock.patch.object(
        auth.requests, "post", return_value=_Response(200, b'{"access_token": "t0ken"}')
    ) as post:
        assert (
            adapter.issue_token("https://uss.example.com", ["scope1", "scope2"])
            == "t0ken"
        )

    assert post.call_args[0][0] == "http://host/token"
    payload = post.call_args[1]["data"]
    assert payload["grant_type"] == "client_credentials"
    assert payload["audience"] == "https://uss.example.com"
    assert payload["scope"] == "scope1 scope2"

    header = jwcrypto.jwt.JWT(
        jwt=payload["client_assertion"], key=_KEY
    ).token.jose_header
    assert header["alg"] == "RS256"
    assert "kid" not in header

    claims = json.loads(
        jwcrypto.jwt.JWT(jwt=payload["client_assertion"], key=_KEY).claims
    )
    assert claims["iss"] == "cli"
    assert claims["sub"] == "cli"
    assert claims["aud"] == "http://host/token"
    assert claims["exp"] == claims["iat"] + 300


def test_jwt_bearer_issue_token_error():
    adapter = auth.PrivateKeyJWT("http://host/token", "cli", key_path=_KEY_PATH)
    with mock.patch.object(
        auth.requests, "post", return_value=_Response(401, b"invalid_grant")
    ):
        with pytest.raises(auth.AccessTokenError):
            adapter.issue_token("https://uss.example.com", ["scope1"])
