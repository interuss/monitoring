import os

from gunicorn.arbiter import Arbiter
from gunicorn.http import Request
from gunicorn.http.wsgi import Response
from gunicorn.workers.base import Worker
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


def pre_request(worker: Worker, req: Request):
    """gunicorn server hook called just before a worker processes the request."""
    logger.debug(
        "gunicorn pre_request from worker {} (OS PID {}): {} {}",
        worker.pid,
        os.getpid(),
        req.method,
        req.path,
    )


def post_request(worker: Worker, req: Request, environ: dict, resp: Response):
    """gunicorn server hook called after a worker processes the request."""
    logger.debug(
        "gunicorn post_request from worker {} (OS PID {}): {} {} -> {}",
        worker.pid,
        os.getpid(),
        req.method,
        req.path,
        resp.status_code,
    )


def worker_abort(worker: Worker):
    """gunicorn server hook called when a worker received the SIGABRT signal."""
    logger.debug(
        "gunicorn worker_abort from worker {} (OS PID {})", worker.pid, os.getpid()
    )


def on_exit(server: Arbiter):
    """gunicorn server hook called just before exiting Gunicorn."""
    logger.debug(
        f"on_exit from process {os.getpid()} with arbiter process {server.pid}"
    )
    webapp.shutdown(None, None)
