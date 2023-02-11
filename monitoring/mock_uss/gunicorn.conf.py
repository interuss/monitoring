import os

from gunicorn.arbiter import Arbiter
from loguru import logger

from monitoring.mock_uss import webapp


def on_starting(server: Arbiter):
    """gunicorn server hook called just before master process is initialized."""
    logger.debug("on_starting")
    webapp.setup()


def when_ready(server: Arbiter):
    """gunicorn server hook called just after the server is started."""
    logger.debug("when_ready")
    webapp.start_periodic_tasks_daemon()


def on_exit(server: Arbiter):
    """gunicorn server hook called just before exiting Gunicorn."""
    logger.debug(
        f"on_exit from process {os.getpid()} with arbiter process {server.pid}"
    )
    webapp.shutdown(None, None)
