import inspect
import os
from typing import Any, Optional, Callable
from loguru import logger

from monitoring.mock_uss.server import MockUSS

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
enabled_services = set()


def import_environment_variable(
    var_name: str,
    required: bool = True,
    default: Optional[str] = None,
    mutator: Optional[Callable[[str], Any]] = None,
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


from monitoring.mock_uss import config
from monitoring.mock_uss import routes as basic_routes

if SERVICE_GEOAWARENESS in webapp.config[config.KEY_SERVICES]:
    enabled_services.add(SERVICE_GEOAWARENESS)
    from monitoring.mock_uss import geoawareness
    from monitoring.mock_uss.geoawareness import routes as geoawareness_routes

if SERVICE_RIDSP in webapp.config[config.KEY_SERVICES]:
    enabled_services.add(SERVICE_RIDSP)
    from monitoring.mock_uss import ridsp
    from monitoring.mock_uss.ridsp import routes as ridsp_routes

if SERVICE_RIDDP in webapp.config[config.KEY_SERVICES]:
    enabled_services.add(SERVICE_RIDDP)
    from monitoring.mock_uss import riddp
    from monitoring.mock_uss.riddp import routes as riddp_routes

if SERVICE_SCDSC in webapp.config[config.KEY_SERVICES]:
    enabled_services.add(SERVICE_SCDSC)
    from monitoring.mock_uss.f3548v21 import routes_scd
    from monitoring.mock_uss.scd_injection import routes as scd_injection_routes

if SERVICE_MESSAGESIGNING in webapp.config[config.KEY_SERVICES]:
    enabled_services.add(SERVICE_MESSAGESIGNING)
    from monitoring.mock_uss import msgsigning
    from monitoring.mock_uss.msgsigning import routes as msgsigning_routes

if SERVICE_INTERACTION_LOGGING in webapp.config[config.KEY_SERVICES]:
    enabled_services.add(SERVICE_INTERACTION_LOGGING)
    from monitoring.mock_uss.interaction_logging import logger as interactions_logger
    from monitoring.mock_uss.interaction_logging import routes_interactions_log

if SERVICE_TRACER in webapp.config[config.KEY_SERVICES]:
    enabled_services.add(SERVICE_TRACER)
    from monitoring.mock_uss import tracer
    from monitoring.mock_uss.tracer import routes as tracer_routes

if SERVICE_VERSIONING in webapp.config[config.KEY_SERVICES]:
    enabled_services.add(SERVICE_VERSIONING)
    from monitoring.mock_uss.versioning import routes as versioning_routes

if SERVICE_FLIGHT_PLANNING in webapp.config[config.KEY_SERVICES]:
    enabled_services.add(SERVICE_FLIGHT_PLANNING)
    from monitoring.mock_uss.flight_planning import routes as flight_planning_routes

msg = (
    "################################################################################\n"
    + "################################ Configuration  ################################\n"
    + "\n".join("## {}: {}".format(key, webapp.config[key]) for key in webapp.config)
    + "\n"
    + "################################################################################"
)
logger.info("Configuration:\n" + msg)
