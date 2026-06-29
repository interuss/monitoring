"""Mint a JWT from the local Dummy OAuth server."""

import requests


def issue_token(endpoint: str, sub: str, audience: str, scopes: list[str]) -> str:
    params = {
        "grant_type": "client_credentials",
        "scope": " ".join(scopes),
        "intended_audience": audience,
        "issuer": "dummy",
        "sub": sub,
    }
    resp = requests.get(endpoint, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()["access_token"]
