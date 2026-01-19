#!env/bin/python3

import os

import requests
from locust import HttpUser
from uas_standards.astm.f3411.v19.constants import Scope as f3411_scope
from uas_standards.astm.f3548.v21.constants import Scope as f3548_scope

from monitoring.monitorlib import auth


class USS(HttpUser):
    # Suggested by Locust 1.2.2 API Docs https://docs.locust.io/en/stable/api.html#locust.User.abstract
    abstract = True
    isa_dict: dict[str, str] = {}
    sub_dict: dict[str, str] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        auth_spec = os.environ.get("AUTH_SPEC")

        if not auth_spec:
            raise Exception(
                "Missing AUTH_SPEC environment variable, please check README"
            )

        # This is a load tester its acceptable to have all the scopes required to operate anything.
        # We are not testing if the scope is incorrect. We are testing if it can handle the load.
        scopes = [
            f3411_scope.Read,
            f3411_scope.Write,
            f3548_scope.StrategicCoordination,
        ]
        oauth_adapter = auth.make_auth_adapter(auth_spec)

        def _auth(
            prepared_request: requests.PreparedRequest,
        ) -> requests.PreparedRequest:
            oauth_adapter.add_headers(prepared_request, scopes)
            return prepared_request

        self.client.auth = _auth
