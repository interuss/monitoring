import base64
import hashlib
import json
import time
from pathlib import Path

import jwt
import pytest
from jwcrypto import jwk

from monitoring.dummy_oauth.app import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_CERTS = REPO_ROOT / "build" / "test-certs"
PUBLIC_KEY = (TEST_CERTS / "auth2.pem").read_bytes()
PARAMS = {"intended_audience": "uss.example.com", "scope": "scope1 scope2"}


@pytest.fixture
def client():
    app = create_app(str(TEST_CERTS / "auth2.key"))
    app.testing = True
    return app.test_client()


def test_token_defaults(client):
    before = int(time.time())
    response = client.get("/token", query_string=PARAMS)
    after = int(time.time())
    assert response.status_code == 200
    claims = jwt.decode(
        response.json["access_token"],
        PUBLIC_KEY,
        algorithms=["RS256"],
        audience=PARAMS["intended_audience"],
        issuer="dummyoauth",
    )
    assert before + 3600 <= claims.pop("exp") <= after + 3600
    assert claims == {
        "aud": PARAMS["intended_audience"],
        "scope": PARAMS["scope"],
        "iss": "dummyoauth",
        "sub": "fake_uss",
    }


@pytest.mark.parametrize("expires", [0, 4102444800])
def test_explicit_claims(client, expires):
    response = client.get(
        "/token",
        query_string={
            **PARAMS,
            "issuer": "my-issuer",
            "sub": "uss1",
            "expire": expires,
        },
    )
    assert response.status_code == 200
    claims = jwt.decode(
        response.json["access_token"],
        PUBLIC_KEY,
        algorithms=["RS256"],
        audience=PARAMS["intended_audience"],
        options={"verify_exp": False},
    )
    assert claims == {
        "aud": PARAMS["intended_audience"],
        "scope": PARAMS["scope"],
        "iss": "my-issuer",
        "sub": "uss1",
        "exp": expires,
    }


@pytest.mark.parametrize("missing", ["intended_audience", "scope"])
def test_missing_parameter(client, missing):
    response = client.get(
        "/token", query_string={k: v for k, v in PARAMS.items() if k != missing}
    )
    assert response.status_code == 400
    assert response.json == {"message": f"Missing `{missing}` query parameter"}


@pytest.mark.parametrize("expires", ["invalid", "", "1.5"])
def test_invalid_expiry(client, expires):
    response = client.get("/token", query_string={**PARAMS, "expire": expires})
    assert response.status_code == 400
    assert "expire" in response.json["message"]


def test_jwks_verifies_token(client):
    response = client.get("/.well-known/jwks.json")
    assert response.status_code == 200
    (public_key,) = response.json["keys"]
    assert set(public_key) == {"kty", "use", "alg", "kid", "n", "e"}
    assert public_key["kty"] == "RSA"
    assert public_key["use"] == "sig"
    assert public_key["alg"] == "RS256"
    canonical = json.dumps(
        {k: public_key[k] for k in ("e", "kty", "n")}, separators=(",", ":")
    ).encode()
    expected_id = base64.urlsafe_b64encode(hashlib.sha256(canonical).digest())
    assert public_key["kid"] == expected_id.decode().rstrip("=")
    token = client.get("/token", query_string=PARAMS).json["access_token"]
    assert jwt.get_unverified_header(token) == {
        "alg": "RS256",
        "typ": "JWT",
        "kid": public_key["kid"],
    }
    jwt.decode(
        token,
        jwt.PyJWK.from_dict(public_key).key,
        algorithms=["RS256"],
        audience=PARAMS["intended_audience"],
    )


def test_configured_signing_key(monkeypatch, tmp_path):
    key = jwk.JWK.generate(kty="RSA", size=2048)
    path = tmp_path / "custom.key"
    path.write_bytes(key.export_to_pem(private_key=True, password=None))
    monkeypatch.setenv("DUMMY_OAUTH_PRIVATE_KEY_FILE", str(path))
    client = create_app().test_client()
    response = client.get("/token", query_string=PARAMS)
    assert response.status_code == 200
    body = response.json
    assert body is not None
    token = body["access_token"]
    jwt.decode(
        token,
        key.export_to_pem(),
        algorithms=["RS256"],
        audience=PARAMS["intended_audience"],
    )
    response = client.get("/.well-known/jwks.json")
    assert response.status_code == 200
    body = response.json
    assert body is not None
    assert body["keys"][0]["kid"] == key.thumbprint()


# This test is AI-generated and has not been closely inspected by a human.
def test_non_rsa_signing_key_rejected(tmp_path):
    key = jwk.JWK.generate(kty="EC", crv="P-256")
    path = tmp_path / "ec.key"
    path.write_bytes(key.export_to_pem(private_key=True, password=None))
    with pytest.raises(ValueError, match="Dummy OAuth requires an RSA private key"):
        create_app(str(path))


# This test is AI-generated and has not been closely inspected by a human.
def test_public_only_signing_key_rejected():
    with pytest.raises(ValueError, match="Dummy OAuth requires an RSA private key"):
        create_app(str(TEST_CERTS / "auth2.pem"))
