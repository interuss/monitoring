import json
import traceback
from typing import List, Dict, Optional

from implicitdict import ImplicitDict, StringBasedDateTime, StringBasedTimeDelta

from monitoring.monitorlib.multiprocessing import SynchronizedValue


class PeriodicTaskStatus(ImplicitDict):
    last_execution_time: Optional[StringBasedDateTime] = None
    period: Optional[StringBasedTimeDelta] = None
    executing: bool = False


class TaskError(ImplicitDict):
    trigger: str
    type: str
    message: str
    stacktrace: str

    @staticmethod
    def from_exception(trigger: str, e: BaseException):
        return TaskError(
            trigger=trigger,
            type=type(e).__name__,
            message=str(e),
            stacktrace="".join(traceback.format_exception(e)),
        )


class Database(ImplicitDict):
    """Simple in-memory pseudo-database tracking the state of the mock system"""

    one_time_tasks: List[str]
    """Names of one-time tasks that a process has already initiated"""

    task_errors: List[TaskError]
    """Information about task errors encountered while running"""

    stopping: bool = False
    """True only when the mock_uss should be stopping"""

    periodic_tasks: Dict[str, PeriodicTaskStatus]
    """Tasks to perform periodically, by name"""

    most_recent_periodic_check: Optional[StringBasedDateTime]
    """Timestamp of most recent time periodic task loop iterated"""


db = SynchronizedValue(
    Database(one_time_tasks=[], task_errors=[], periodic_tasks={}),
    decoder=lambda b: ImplicitDict.parse(json.loads(b.decode("utf-8")), Database),
)
