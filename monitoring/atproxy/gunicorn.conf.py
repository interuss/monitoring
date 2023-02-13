import os

from gunicorn.http import Request
from gunicorn.http.wsgi import Response
from gunicorn.workers.base import Worker
from loguru import logger


def pre_request(worker: Worker, req: Request):
    """gunicorn server hook called just before a worker processes the request."""
    logger.debug("gunicorn pre_request from worker {} (OS PID {}): {} {}", worker.pid, os.getpid(), req.method, req.path)


def post_request(worker: Worker, req: Request, environ: dict, resp: Response):
    """gunicorn server hook called after a worker processes the request."""
    logger.debug("gunicorn post_request from worker {} (OS PID {}): {} {} -> {}", worker.pid, os.getpid(), req.method, req.path, resp.status_code)


def worker_abort(worker: Worker):
    """gunicorn server hook called when a worker received the SIGABRT signal."""
    logger.debug("gunicorn worker_abort from worker {} (OS PID {})", worker.pid, os.getpid())
