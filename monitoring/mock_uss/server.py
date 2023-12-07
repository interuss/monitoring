import traceback
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from multiprocessing import Process
import os
import signal
import time
from typing import Callable, Dict, Optional, Tuple

import arrow
import flask
from jinja2 import FileSystemLoader
from loguru import logger

from implicitdict import StringBasedDateTime, StringBasedTimeDelta
from .database import db, PeriodicTaskStatus, TaskError, Database


MAX_PERIODIC_LATENCY = timedelta(seconds=5)


def _get_trace(e: Exception) -> str:
    return "".join(traceback.format_exception(e))


class TaskTrigger(str, Enum):
    Setup = "Setup"
    Shutdown = "Shutdown"


@dataclass
class OneTimeServerTask(object):
    run: Callable[[], None]
    trigger: TaskTrigger


@dataclass
class PeriodicServerTask(object):
    run: Callable[[], None]


class MockUSS(flask.Flask):
    _pid: int
    _one_time_tasks: Dict[str, OneTimeServerTask]
    _periodic_tasks: Dict[str, PeriodicServerTask]

    jinja_loader = FileSystemLoader(
        [
            os.path.abspath(os.path.join(os.path.dirname(__file__), relpath))
            for relpath in ("templates", "../monitorlib/html/templates")
        ]
    )

    def __init__(self, *args, **kwargs):
        self._pid = os.getpid()
        logger.info(f"Initializing MockUSS from process {self._pid}")
        self._one_time_tasks = {}
        self._periodic_tasks = {}
        super(MockUSS, self).__init__(*args, **kwargs)

    def add_one_time_task(
        self, task: Callable[[], None], name: str, trigger: TaskTrigger
    ):
        self._one_time_tasks[name] = OneTimeServerTask(run=task, trigger=trigger)

    def setup_task(self, task_name: str):
        """Decorator that causes the decorated function to be executed once at server start.

        Args:
            task_name: Unique name of this setup task (for logs, etc)
        """

        def setup_task_decorator(func):
            self.add_one_time_task(func, task_name, TaskTrigger.Setup)
            return func

        return setup_task_decorator

    def shutdown_task(self, task_name: str):
        """Decorator that causes the decorated function to be executed once at server shutdown.

        Args:
            task_name: Unique name of this shutdown task (for logs, etc)
        """

        def shutdown_task_decorator(func):
            self.add_one_time_task(func, task_name, TaskTrigger.Shutdown)
            return func

        return shutdown_task_decorator

    def _run_one_time_tasks(self, trigger: TaskTrigger):
        tasks: Dict[str, OneTimeServerTask] = {}
        with db as tx:
            for task_name, task in self._one_time_tasks.items():
                if task.trigger == trigger and task_name not in tx.one_time_tasks:
                    tx.one_time_tasks.append(task_name)
                    tasks[task_name] = task
        if not tasks:
            logger.info(f"No {trigger} tasks to initiate from process ID {os.getpid()}")
            return
        logger.info(
            "Running {} {} task{}", len(tasks), trigger, "s" if len(tasks) > 1 else ""
        )
        for task_name, setup_task in tasks.items():
            logger.info(
                f"Initiating '{task_name}' {trigger} task from process ID {os.getpid()}"
            )
            try:
                setup_task.run()
            except Exception as e:
                with db as tx:
                    tx.task_errors.append(TaskError.from_exception(trigger, e))
                if trigger == TaskTrigger.Shutdown:
                    logger.error(
                        f"{type(e).__name__} error in '{task_name}' on process ID {os.getpid()} while shutting down mock_uss: {str(e)}\n{_get_trace(e)}"
                    )
                else:
                    logger.error(
                        f"Stopping mock_uss due to {type(e).__name__} error in '{task_name}' {trigger} task on process ID {os.getpid()}: {str(e)}\n{_get_trace(e)}"
                    )
                    self.stop()
                    return
        logger.info(
            "Completed running {} {} task{}",
            len(tasks),
            trigger,
            "s" if len(tasks) > 1 else "",
        )

    def setup(self):
        self._run_one_time_tasks(TaskTrigger.Setup)

    def declare_periodic_task(self, task: Callable[[], None], name: str):
        self._periodic_tasks[name] = PeriodicServerTask(run=task)

    def periodic_task(self, task_name: str):
        """Decorator that causes the decorated function to be executed repeatedly in the background.

        Args:
            task_name: Unique name of this periodic task (for logs, etc)
        """

        def periodic_task_decorator(func):
            self.declare_periodic_task(func, task_name)
            return func

        return periodic_task_decorator

    def set_task_period(self, task_name: str, period: Optional[timedelta]):
        if task_name not in self._periodic_tasks:
            raise ValueError(
                f"Periodic task '{task_name}' is not declared, so its period cannot be set"
            )
        with db as tx:
            assert isinstance(tx, Database)
            if task_name not in tx.periodic_tasks:
                tx.periodic_tasks[task_name] = PeriodicTaskStatus()
            tx.periodic_tasks[task_name].period = (
                StringBasedTimeDelta(period) if period is not None else None
            )

    def start_periodic_tasks_daemon(self):
        if not self._periodic_tasks:
            logger.info(
                f"Not starting periodic task daemon from process {os.getpid()} because there are no periodic tasks declared"
            )
        else:
            logger.info(f"Initiating periodic task daemon from process {os.getpid()}")
            p = Process(target=lambda: self._periodic_tasks_daemon_loop())
            p.start()

    def _periodic_tasks_daemon_loop(self):
        try:
            while True:
                # Determine what to do on this loop (execute task or wait)
                task_to_execute = None
                next_check = None
                with db as tx:
                    assert isinstance(tx, Database)
                    tx.most_recent_periodic_check = StringBasedDateTime(
                        datetime.utcnow()
                    )

                    # Cancel the loop if we're stopping
                    if tx.stopping:
                        break

                    # Find the earliest scheduled task
                    earliest_task: Optional[
                        Tuple[str, datetime, PeriodicTaskStatus]
                    ] = None
                    for task_name, task in tx.periodic_tasks.items():
                        if task.executing:
                            # Don't consider executing tasks that are already executing
                            continue
                        if task_name not in self._periodic_tasks:
                            logger.error(
                                "Periodic task '{}' was not defined at application start and therefore cannot be run periodically",
                                task_name,
                            )
                            task.last_execution_time = StringBasedDateTime(
                                arrow.utcnow()
                            )
                            continue
                        if task.period is None:
                            # Skip periodic tasks without periods
                            continue
                        if task.last_execution_time is None:
                            # This is the first time this task has been run; pick it immediately
                            earliest_task = (task_name, arrow.utcnow().datetime, task)
                            break
                        t_next = (
                            task.last_execution_time.datetime + task.period.timedelta
                        )
                        if not earliest_task or t_next < earliest_task[1]:
                            # This task is more urgent than the one we were looking at before
                            earliest_task = (task_name, t_next, task)
                    if earliest_task:
                        task_name, t_execute, task = earliest_task
                        if t_execute <= arrow.utcnow().datetime:
                            # We should execute this task immediately
                            tx.periodic_tasks[task_name] = PeriodicTaskStatus(
                                last_execution_time=StringBasedDateTime(
                                    arrow.utcnow().datetime
                                ),
                                period=task.period,
                                executing=True,
                            )
                            task_to_execute = task_name
                        else:
                            # We need to wait some time before executing this task
                            next_check = t_execute
                # </with db as tx>

                if task_to_execute:
                    # Execute the selected task right now
                    logger.debug(
                        f"Executing '{task_to_execute}' periodic task from process {os.getpid()}"
                    )
                    self._periodic_tasks[task_to_execute].run()
                    with db as tx:
                        periodic_task = tx.periodic_tasks[task_to_execute]
                        periodic_task.executing = False
                        if periodic_task.period.timedelta.total_seconds() == 0:
                            periodic_task.last_execution_time = StringBasedDateTime(
                                arrow.utcnow().datetime
                            )
                else:
                    # Wait until another task may be ready to execute
                    if next_check:
                        dt = min(
                            MAX_PERIODIC_LATENCY, next_check - arrow.utcnow().datetime
                        )
                    else:
                        dt = MAX_PERIODIC_LATENCY
                    if dt.total_seconds() > 0:
                        time.sleep(dt.total_seconds())
        except Exception as e:
            logger.error(
                f"Shutting down mock_uss due to {type(e).__name__} error while executing '{task_to_execute}' periodic task: {str(e)}\n{_get_trace(e)}"
            )
            with db as tx:
                tx.task_errors.append(TaskError.from_exception(TaskTrigger.Setup, e))
            self.stop()
        finally:
            logger.info(f"Periodic task daemon for process {os.getpid()} exited")

    def is_stopping(self) -> bool:
        return db.value.stopping

    def stop(self):
        send_signal = False
        with db as tx:
            if not tx.stopping:
                send_signal = True
                tx.stopping = True
        if send_signal:
            logger.info(
                f"Initiating shutdown of MockUSS process {self._pid} from process {os.getpid()}"
            )
            os.kill(self._pid, signal.SIGTERM)
        else:
            logger.info(
                f"Process {os.getpid()} detected that server shutdown was already in process when stop was requested"
            )

    def shutdown(self, signal_number: Optional[int], stack):
        if os.getpid() != self._pid:
            logger.debug(f"Process {os.getpid()} skipping shutdown procedure")
            return
        db_value = db.value
        if db_value.stopping:
            logger.debug(f"Process {os.getpid()} stopping with signal {signal_number}")
            self._run_one_time_tasks(TaskTrigger.Shutdown)
        else:
            logger.debug(
                f"Process {os.getpid()} stopped with signal {signal_number} while MockUSS server was not stopping"
            )
        task_errors = db_value.task_errors
        for task_error in task_errors:
            logger.error(
                f"Server was shut down due to {task_error.type} error during {task_error.trigger}: {task_error.message}\n{task_error.stacktrace}"
            )
        logger.warning(
            "AssertionErrors with 'can only join a child process' are spurious; see https://github.com/benoitc/gunicorn/issues/2919"
        )
