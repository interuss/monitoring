import functools

from loguru import logger

from monitoring.mock_uss import require_config_value, webapp
from monitoring.mock_uss.config import KEY_DSS_URL, KEY_AUTH_SPEC
from monitoring.monitorlib import auth
from monitoring.monitorlib.infrastructure import UTMClientSession

from monitoring.mock_uss import webapp
from monitoring.mock_uss.config import KEY_LOG_DIR

require_config_value(KEY_DSS_URL)
require_config_value(KEY_AUTH_SPEC)

utm_client = UTMClientSession(
    webapp.config[KEY_DSS_URL],
    auth.make_auth_adapter(webapp.config[KEY_AUTH_SPEC]),
)


def no_log_interaction(function):
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        if len(args) > 0:
            logger.debug(f"args passed to wrapper from {function.__name__} - {args}")
        else:
            logger.debug("no args")

        if kwargs:
            logger.debug(
                f"kwargs passed to wrapper from {function.__name__} - {kwargs}"
            )
        return function(*args, **kwargs)

    return wrapper


if KEY_LOG_DIR in webapp.config:
    logger.debug(f"KEY_LOG_DIR - {KEY_LOG_DIR} is in config")
    from monitoring.mock_uss.interuss_logging import scd_log as scd_client
    from monitoring.mock_uss.interuss_logging.logger import log_flask_interaction as log
else:
    logger.debug(f"KEY_LOG_DIR - {KEY_LOG_DIR} not in config")
    from monitoring.monitorlib.clients import scd as scd_client
    from . import no_log_interaction as log
