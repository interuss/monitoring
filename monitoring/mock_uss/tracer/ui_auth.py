from dataclasses import dataclass
from typing import List, Union

from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

from monitoring.mock_uss import import_environment_variable, webapp

ui_auth = HTTPBasicAuth()

KEY_TRACER_UI_USERS = "MOCK_USS_TRACER_UI_USERS"
"""Environment variable containing configuration of users allowed to access the UI.

Form: {USER1}[@{ROLE1}[,{ROLE2}[,{ROLE3}]]]={PASSWORD1};{USER2}[@{ROLE1}[,{ROLE2}[,{ROLE3}]]]={PASSWORD2}

Example: admin@admin=admin;user1@viewer=avalidpassword;user2@viewer=anotherpassword
"""

import_environment_variable(KEY_TRACER_UI_USERS, required=False, default="")


@dataclass
class User(object):
    username: str
    password_hash: str
    roles: List[str]

    def is_admin(self) -> bool:
        return "admin" in self.roles


def _get_users() -> List[User]:
    users = []
    user_strings = webapp.config.get(KEY_TRACER_UI_USERS).split(";")
    for user_string in user_strings:
        if not user_string.strip():
            continue
        if "=" not in user_string:
            raise ValueError(f"Invalid tracer UI user string provided: `{user_string}`")
        name_and_roles, password = user_string.split("=")
        if "@" in name_and_roles:
            name, roles_string = name_and_roles.split("@")
            roles = [r.strip() for r in roles_string.split(",")]
        else:
            name = name_and_roles
            roles = []
        password_hash = generate_password_hash(password.strip())
        users.append(User(username=name, password_hash=password_hash, roles=roles))
    return users


@ui_auth.verify_password
def verify_password(username: str, password: str) -> Union[bool, User]:
    user = [u for u in _get_users() if u.username == username]
    if not user:
        return False  # No matching user
    if check_password_hash(user[0].password_hash, password):
        return user[0]
    else:
        return False  # Matching user, but wrong password


@ui_auth.get_user_roles
def get_user_roles(user: User) -> List[str]:
    return user.roles
