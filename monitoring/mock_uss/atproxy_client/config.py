from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

from monitoring.mock_uss import import_environment_variable


@dataclass
class BasicAuth(object):
    username: str
    password: str

    @property
    def tuple(self) -> Tuple[str, str]:
        return self.username, self.password

    @staticmethod
    def create(str_value) -> BasicAuth:
        auth_components = tuple(s.strip() for s in str_value.split(":"))
        if len(auth_components) != 2:
            raise ValueError(
                f'Invalid basic auth specification; expected <username>:<password> but instead found "{str_value}"'
            )
        return BasicAuth(username=auth_components[0], password=auth_components[1])


KEY_ATPROXY_BASE_URL = "MOCK_USS_ATPROXY_BASE_URL"
KEY_ATPROXY_BASIC_AUTH = "MOCK_USS_ATPROXY_BASIC_AUTH"

import_environment_variable(KEY_ATPROXY_BASE_URL)
import_environment_variable(KEY_ATPROXY_BASIC_AUTH, mutator=BasicAuth.create)
