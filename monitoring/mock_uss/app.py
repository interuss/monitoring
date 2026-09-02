import inspect
import os
import re
from collections.abc import Callable
from typing import Any

# Because mock_uss uses gevent, we need to monkey-patch before anything else is loaded.
# https://www.gevent.org/intro.html#monkey-patching
from gevent import monkey

monkey.patch_all()

from loguru import logger  # noqa E402
from werkzeug.middleware.proxy_fix import ProxyFix  # noqa E402

from monitoring.mock_uss.server import MockUSS  # noqa E402

SERVICE_GEOAWARENESS = "geoawareness"
SERVICE_RIDSP = "ridsp"
SERVICE_RIDDP = "riddp"
SERVICE_SCDSC = "scdsc"
SERVICE_MESSAGESIGNING = "msgsigning"
SERVICE_TRACER = "tracer"
SERVICE_INTERACTION_LOGGING = "interaction_logging"
SERVICE_VERSIONING = "versioning"
SERVICE_FLIGHT_PLANNING = "flight_planning"

webapp = MockUSS(__name__)
webapp.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)
if os.environ.get("MOCK_USS_PROXY_VALUES"):
    values = os.environ.get("MOCK_USS_PROXY_VALUES", "").split(",")
    kwargs = {v.split("=")[0].strip(): int(v.split("=")[1]) for v in values}
    webapp.wsgi_app = ProxyFix(webapp.wsgi_app, **kwargs)
enabled_services = set()


def import_environment_variable(
    var_name: str,
    required: bool = True,
    default: str | None = None,
    mutator: Callable[[str], Any] | None = None,
) -> None:
    """Import a value from a named environment variable into the webapp configuration.

    Args:
        var_name: Environment variable name (key).  Also used as the webapp configuration key for that variable.
        required: Whether the variable must be specified by the user.  If True, a ValueError will be raised if the
            variable is not specified by the user.  If False, the webapp configuration will not be populated if no
            default is provided.  If default is specified, the default value is treated as specification by the user.
        default: If the variable is not required, then use this value when it is not specified by the user.  The default
            value should be the string from the environment variable rather than the output of the mutator, if present.
        mutator: If specified, apply this function to the string value of the environment variable to obtain the
            variable to actually store in the configuration.
    """
    if var_name in os.environ:
        str_value = os.environ[var_name]
    elif default is not None:
        str_value = default
    elif required:
        stack = inspect.stack()
        raise ValueError(
            f"System cannot proceed because required environment variable '{var_name}' was not found.  Required from {stack[1].filename}:{stack[1].lineno}"
        )
    else:
        str_value = None

    if str_value is not None:
        webapp.config[var_name] = str_value if mutator is None else mutator(str_value)


def require_config_value(config_key: str) -> None:
    if config_key not in webapp.config:
        stack = inspect.stack()
        raise ValueError(
            f"System cannot proceed because required configuration key '{config_key}' was not found.  Required from {stack[1].filename}:{stack[1].lineno}"
        )


from monitoring.mock_uss import config  # noqa E402
from monitoring.mock_uss import logging as logging  # noqa E402
from monitoring.mock_uss import routes as basic_routes  # noqa F401,F402

if SERVICE_GEOAWARENESS in webapp.config[config.KEY_SERVICES]:
    enabled_services.add(SERVICE_GEOAWARENESS)
    from monitoring.mock_uss import geoawareness as geoawareness
    from monitoring.mock_uss.geoawareness import (
        routes as geoawareness_routes,  # noqa F401
    )

if SERVICE_RIDSP in webapp.config[config.KEY_SERVICES]:
    enabled_services.add(SERVICE_RIDSP)
    from monitoring.mock_uss import ridsp as ridsp
    from monitoring.mock_uss.ridsp import routes as ridsp_routes  # noqa F401

if SERVICE_RIDDP in webapp.config[config.KEY_SERVICES]:
    enabled_services.add(SERVICE_RIDDP)
    from monitoring.mock_uss import riddp as riddp
    from monitoring.mock_uss.riddp import routes as riddp_routes  # noqa F401

if SERVICE_SCDSC in webapp.config[config.KEY_SERVICES]:
    enabled_services.add(SERVICE_SCDSC)
    from monitoring.mock_uss.f3548v21 import routes_scd as routes_scd
    from monitoring.mock_uss.scd_injection import (
        routes as scd_injection_routes,  # noqa F401
    )

if SERVICE_MESSAGESIGNING in webapp.config[config.KEY_SERVICES]:
    enabled_services.add(SERVICE_MESSAGESIGNING)
    from monitoring.mock_uss import msgsigning as msgsigning  # noqa F401
    from monitoring.mock_uss.msgsigning import routes as msgsigning_routes  # noqa F401

if SERVICE_INTERACTION_LOGGING in webapp.config[config.KEY_SERVICES]:
    enabled_services.add(SERVICE_INTERACTION_LOGGING)
    from monitoring.mock_uss.interaction_logging import logger as interactions_logger  # noqa F401
    from monitoring.mock_uss.interaction_logging import (
        routes_interactions_log as routes_interactions_log,
    )

    logger.info("Interaction logging enabled")
else:
    logger.info("Interaction logging disabled")

if SERVICE_TRACER in webapp.config[config.KEY_SERVICES]:
    enabled_services.add(SERVICE_TRACER)
    from monitoring.mock_uss import tracer as tracer
    from monitoring.mock_uss.tracer import routes as tracer_routes  # noqa F401

if SERVICE_VERSIONING in webapp.config[config.KEY_SERVICES]:
    enabled_services.add(SERVICE_VERSIONING)
    from monitoring.mock_uss.versioning import routes as versioning_routes  # noqa F401

if SERVICE_FLIGHT_PLANNING in webapp.config[config.KEY_SERVICES]:
    enabled_services.add(SERVICE_FLIGHT_PLANNING)
    from monitoring.mock_uss.flight_planning import routes as flight_planning_routes  # noqa F401


_SECRET_NAME_RE = re.compile(
    r"API|AUTH|TOKEN|KEY|SECRET|PASS|SIGNATURE|HTTP_COOKIE",
    flags=re.I,
)
_SAFE_KEYS = ["MOCK_USS_PUBLIC_KEY", "MOCK_USS_TOKEN_AUDIENCE"]

# Extract the userinfo part of an URI
_USERINFO_RE = re.compile(r"(?<=://)[^/@\s]*:[^/@\s]*@")

_ARITY = {
    "NoAuth": 2,
    "InvalidTokenSignatureAuth": 1,
    "DummyOAuth": 2,
    "ServiceAccount": 2,
    "ServiceAccountImpersonation": 2,
    "SignedRequest": 6,
    "UsernamePassword": 4,
    "ClientIdClientSecret": 4,
    "Keycloak": 3,
    "FlightPassport": 4,
    "PrivateKeyJWT": 5,
}

_SECRETS = {
    "UsernamePassword": (2, "password"),
    "ClientIdClientSecret": (2, "client_secret"),
    "Keycloak": (2, "client_secret"),
    "FlightPassport": (2, "client_secret"),
    "PrivateKeyJWT": (3, "key"),
}


def sanitize_secrets(key, value):
    """Ensure value is free of sensitive values:

    * Authentication information is removed from URLs
    * Key names are used to detect secrets and obfuscate the value
    * MOCK_USS_AUTH_SPEC value secrets are removed
    * Unrecognized elements are escaped as a safe fallback"""

    if key != "MOCK_USS_AUTH_SPEC":  # Non-auth spec case
        if (
            key not in _SAFE_KEYS
            and _SECRET_NAME_RE.search(  # Name contains key/secret/etc...
                key,
            )
        ):
            return "***"

        if not isinstance(value, str):  # Value may be non-string
            return value

        return _USERINFO_RE.sub("***@", value)

    from monitoring.monitorlib.auth import SPEC_RE  # Loaded here due to circular import

    m = SPEC_RE.match(value)  # Try to parse an AuthSpec
    if m is None:
        return "***"

    name, param_string = m.group(1), m.group(2)
    params = [p.strip() for p in param_string.split(",")]

    if (
        name not in _ARITY or len(params) > _ARITY[name]
    ):  # Unknown adapter, we escape everything
        hidden = [
            p.split("=", 1)[0].strip() + "=***" if "=" in p else "***" for p in params
        ]
        return "{}({})".format(name, ", ".join(hidden))

    pos_index, kwarg = _SECRETS.get(name, (None, None))
    out = []
    pos = 0
    for p in params:  # For each parameter
        if "=" in p:  # Named parameter
            k, v = p.split("=", 1)
            k = k.strip()
            out.append(
                k + "=***"
                if k == kwarg
                else k + "=" + _USERINFO_RE.sub("***@", v.strip())
            )
        else:  # Positional parameter
            out.append("***" if pos == pos_index else _USERINFO_RE.sub("***@", p))
            pos += 1

    return "{}({})".format(name, ", ".join(out))


msg = (
    "################################################################################\n"
    + "################################ Configuration  ################################\n"
    + "\n".join(
        f"## {key}: {sanitize_secrets(key, webapp.config[key])}"
        for key in webapp.config
    )
    + "\n"
    + "################################################################################"
)
logger.info("Configuration:\n" + msg)
