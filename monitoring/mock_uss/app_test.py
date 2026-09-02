import pytest

from monitoring.mock_uss.app import sanitize_secrets

K = "MOCK_USS_AUTH_SPEC"


@pytest.mark.parametrize(
    "key",
    [
        "API_URL",
        "AUTH_SPEC",
        "TOKEN_ENDPOINT",
        "KEY_PATH",
        "SECRET_KEY",
        "PASSWORD",
        "PASS",
        "SIGNATURE_STYLE",
        "HTTP_COOKIE",
        "secret_key",
        "api_key",
        "DB_PASSWORD",
        "USS_AUTH_TOKEN",
        "MY_SECRET",
        "MY_API",
        "X_AUTH_SPEC",
    ],
)
def test_sensitive_key_hidden(key):
    assert sanitize_secrets(key, "randomvalue") == "***"


@pytest.mark.parametrize("key", ["PORT", "DEBUG", "USS_QUALIFIER_URL"])
def test_insensitive_key_untouched(key):
    assert sanitize_secrets(key, "randomvalue") == "randomvalue"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("NoAuth(sub=uss1)", "NoAuth(sub=uss1)"),
        (
            "InvalidTokenSignatureAuth(uss_unsigned)",
            "InvalidTokenSignatureAuth(uss_unsigned)",
        ),
        (
            "DummyOAuth(http://oauth.authority.localutm:8085/token,uss2)",
            "DummyOAuth(http://oauth.authority.localutm:8085/token, uss2)",
        ),
        (
            "ServiceAccount(http://host/token,/secrets/sa.json)",
            "ServiceAccount(http://host/token, /secrets/sa.json)",
        ),
        (
            "ServiceAccountImpersonation(http://host/token,sa@example.com)",
            "ServiceAccountImpersonation(http://host/token, sa@example.com)",
        ),
        (
            "SignedRequest(http://host/token,client,/keys/k.pem,https://host/c.crt)",
            "SignedRequest(http://host/token, client, /keys/k.pem, https://host/c.crt)",
        ),
    ],
)
def test_no_secret_untouched(value, expected):
    assert sanitize_secrets(K, value) == expected


def test_username_password_positional():
    assert (
        sanitize_secrets(K, "UsernamePassword(http://host/token,alice,hunter2,cli)")
        == "UsernamePassword(http://host/token, alice, ***, cli)"
    )


def test_username_password_kwarg():
    assert (
        sanitize_secrets(
            K,
            "UsernamePassword(http://host/token,alice,client_id=cli,password=hunter2)",
        )
        == "UsernamePassword(http://host/token, alice, client_id=cli, password=***)"
    )


@pytest.mark.parametrize("name", ["ClientIdClientSecret", "Keycloak", "FlightPassport"])
def test_client_secret_positional(name):
    assert (
        sanitize_secrets(K, f"{name}(http://host/token,cli,s3cr3t)")
        == f"{name}(http://host/token, cli, ***)"
    )


def test_client_secret_kwarg_out_of_order():
    assert (
        sanitize_secrets(
            K,
            "Keycloak(client_secret=s3cr3t,token_endpoint=http://host/token,client_id=cli)",
        )
        == "Keycloak(client_secret=***, token_endpoint=http://host/token, client_id=cli)"
    )


def test_client_secret_mixed_with_trailing_positional():
    assert (
        sanitize_secrets(
            K,
            "ClientIdClientSecret(http://host/token,cli,s3cr3t,send_request_as_data=true)",
        )
        == "ClientIdClientSecret(http://host/token, cli, ***, send_request_as_data=true)"
    )


def test_jwt_bearer_key_args():
    assert (
        sanitize_secrets(
            K, "PrivateKeyJWT(http://host/token,cli,/auth/uss1.key,eyJrdHkiOiJSU0EifQ)"
        )
        == "PrivateKeyJWT(http://host/token, cli, /auth/uss1.key, ***)"
    )


def test_jwt_bearer_key_kwarg():
    assert (
        sanitize_secrets(
            K, "PrivateKeyJWT(http://host/token,cli,key=eyJrdHkiOiJSU0EifQ,key_id=k1)"
        )
        == "PrivateKeyJWT(http://host/token, cli, key=***, key_id=k1)"
    )


def test_unknown_adapter_hides_everything():
    assert (
        sanitize_secrets(K, "MysteryAuth(http://host/token,cli,whatever,foo=bar)")
        == "MysteryAuth(***, ***, ***, foo=***)"
    )


@pytest.mark.parametrize(
    "value",
    ["", "not a spec", "DummyOAuth(unclosed", "DummyOAuth(a) trailing"],
)
def test_malformed_hidden(value):
    assert sanitize_secrets(K, value) == "***"


def test_other_key_untouched():
    assert sanitize_secrets(
        "PORT", "UsernamePassword(http://host/token,alice,hunter2,cli)"
    ) == ("UsernamePassword(http://host/token,alice,hunter2,cli)")


@pytest.mark.parametrize(
    "value,expected",
    [
        (
            "UsernamePassword(http://host/token,alice,pa,ss,cli)",
            "UsernamePassword(***, ***, ***, ***, ***)",
        ),
        ("DummyOAuth(http://host/token,uss2,extra)", "DummyOAuth(***, ***, ***)"),
        ("NoAuth(a,b,c)", "NoAuth(***, ***, ***)"),
    ],
)
def test_too_many_params_hidden(value, expected):
    assert sanitize_secrets(K, value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (
            "DummyOAuth(https://user:pw@host/token,uss2)",
            "DummyOAuth(https://***@host/token, uss2)",
        ),
        (
            "Keycloak(token_endpoint=https://user:pw@host/token,client_id=cli,client_secret=s3cr3t)",
            "Keycloak(token_endpoint=https://***@host/token, client_id=cli, client_secret=***)",
        ),
    ],
)
def test_url_userinfo_hidden(value, expected):
    assert sanitize_secrets(K, value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        ("https://user:pw@host/path", "https://***@host/path"),
        ("http://user:pw@host:8085/token", "http://***@host:8085/token"),
        ("https://host/path", "https://host/path"),
        ("sa@example.com", "sa@example.com"),
    ],
)
def test_userinfo_hidden_on_unfiltered_key(value, expected):
    assert sanitize_secrets("USS_QUALIFIER_URL", value) == expected
