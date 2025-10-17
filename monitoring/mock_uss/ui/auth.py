import json
from dataclasses import dataclass
from functools import wraps

import flask
import flask_login
import requests
from flask_login import LoginManager
from loguru import logger
from oauthlib.oauth2 import WebApplicationClient
from werkzeug.security import check_password_hash, generate_password_hash

from monitoring.mock_uss.app import import_environment_variable, webapp

login_manager = LoginManager()
login_manager.init_app(webapp)

KEY_GOOGLE_OAUTH_CLIENT_ID = "GOOGLE_OAUTH_CLIENT_ID"
KEY_GOOGLE_OAUTH_CLIENT_SECRET = "GOOGLE_OAUTH_CLIENT_SECRET"
import_environment_variable(KEY_GOOGLE_OAUTH_CLIENT_ID, required=False, default="")
import_environment_variable(KEY_GOOGLE_OAUTH_CLIENT_SECRET, required=False, default="")

GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"


def _get_oauth_client() -> WebApplicationClient | None:
    client_id = webapp.config.get(KEY_GOOGLE_OAUTH_CLIENT_ID)
    client_secret = webapp.config.get(KEY_GOOGLE_OAUTH_CLIENT_SECRET)
    if client_id and client_secret:
        logger.info(
            f"Using Google single sign-on for mock_uss user interface; OAuth client ID {client_id}"
        )
        return WebApplicationClient(client_id)
    return None


oauth_client = _get_oauth_client()


KEY_UI_USERS = "MOCK_USS_UI_USERS"
"""Environment variable containing configuration of users allowed to access the UI.

Form: {USER1}[:{ROLE1}[,{ROLE2}[,{ROLE3}]]][={PASSWORD1}];{USER2}[:{ROLE1}[,{ROLE2}[,{ROLE3}]]][={PASSWORD2}]

Example: admin:admin=admin;user1:viewer=avalidpassword;user2:viewer=anotherpassword;ssouser@gmail.com:viewer
"""

import_environment_variable(KEY_UI_USERS, required=False, default="")


@dataclass
class User(flask_login.UserMixin):
    username: str
    password_hash: str | None
    roles: list[str]

    def get_id(self) -> str:
        return self.username

    def is_admin(self) -> bool:
        return "admin" in self.roles


def _get_users() -> list[User]:
    users = []
    user_strings = (webapp.config.get(KEY_UI_USERS) or "").split(";")
    for user_string in user_strings:
        if not user_string.strip():
            continue
        if "=" not in user_string:
            name_and_roles = user_string
            password = None
        else:
            name_and_roles, password = user_string.split("=")
        if ":" in name_and_roles:
            name, roles_string = name_and_roles.split(":")
            roles = [r.strip() for r in roles_string.split(",")]
        else:
            name = name_and_roles
            roles = []
        if password is not None:
            password_hash = generate_password_hash(password.strip())
        else:
            password_hash = None
        users.append(User(username=name, password_hash=password_hash, roles=roles))
    return users


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    users = [u for u in _get_users() if u.username == user_id]
    if users:
        return users[0]
    else:
        return None


def _get_provider_cfg() -> dict:
    return requests.get(GOOGLE_DISCOVERY_URL).json()


@webapp.route("/ui/login")
def ui_login():
    if oauth_client:
        provider_cfg = _get_provider_cfg()
        authorization_endpoint = provider_cfg["authorization_endpoint"]
        request_uri = oauth_client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=flask.request.base_url + "/callback",
            scope=["openid", "email", "profile"],
        )
        return flask.redirect(request_uri)
    else:
        return flask.render_template("ui/username_password_login.html")


@webapp.route("/ui/login/usernamepassword", methods=["POST"])
def ui_login_usernamepassword():
    if "username" not in flask.request.form or "password" not in flask.request.form:
        return "Invalid login request", 400
    users = [u for u in _get_users() if u.username == flask.request.form["username"]]
    if not users:
        flask.flash("Invalid username/password combination")
        return flask.redirect(flask.url_for("ui_login"))
    if users[0].password_hash and check_password_hash(
        users[0].password_hash, flask.request.form["password"]
    ):
        flask_login.login_user(users[0])
        return flask.redirect(flask.url_for("ui_login_successful"))
    else:
        flask.flash("Invalid username/password combination")
        return flask.redirect(flask.url_for("ui_login"))


@webapp.route("/ui/login/callback")
def ui_login_callback():
    if not oauth_client:
        return "Not in oauth mode", 400

    if "code" not in flask.request.args:
        return "Missing `code` in request arguments", 400
    code = flask.request.args.get("code")

    # Get token using code
    provider_cfg = _get_provider_cfg()
    token_endpoint = provider_cfg["token_endpoint"]
    token_url, headers, body = oauth_client.prepare_token_request(
        token_endpoint,
        authorization_response=flask.request.url,
        redirect_url=flask.request.base_url,
        code=code,
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(
            webapp.config.get(KEY_GOOGLE_OAUTH_CLIENT_ID, ""),
            webapp.config.get(KEY_GOOGLE_OAUTH_CLIENT_SECRET, ""),
        ),
    )
    oauth_client.parse_request_body_response(json.dumps(token_response.json()))

    # Get user info using token
    userinfo_endpoint = provider_cfg["userinfo_endpoint"]
    uri, headers, body = oauth_client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)
    userinfo = userinfo_response.json()
    if not userinfo.get("email_verified", False):
        return "User email not verified", 400
    username = userinfo["email"]

    # Log user in
    users = [u for u in _get_users() if u.username == username]
    if not users:
        return (
            f"{userinfo['email']} is not an enrolled user of this application; contact the site admin to be enrolled",
            401,
        )
    flask_login.login_user(users[0])
    return flask.redirect(flask.url_for("ui_login_successful"))


def login_required(
    _func=None, *, role: str | None = None, roles: list[str] | None = None
):
    if role and roles:
        raise ValueError("Only one of `role` or `roles` may be specified")
    if role:
        roles = [role]

    def decorator(f):
        @wraps(f)
        def wrap(*args, **kwargs):
            authorized = False
            if flask_login.current_user.is_authenticated:
                if roles:
                    authorized = any(r in flask_login.current_user.roles for r in roles)
                else:
                    authorized = True
            if authorized:
                return f(*args, **kwargs)
            else:
                return flask.redirect(flask.url_for("ui_login"))

        return wrap

    if _func is None:
        return decorator
    else:
        return decorator(_func)


@webapp.route("/ui/login_successful")
@login_required()
def ui_login_successful():
    return flask.render_template(
        "ui/logged_in.html", current_user=flask_login.current_user
    )


@webapp.route("/logout")
@login_required()
def ui_logout():
    flask_login.logout_user()
    return flask.redirect(flask.url_for("status"))
