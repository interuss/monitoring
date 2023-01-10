import json

from monitoring.monitorlib.multiprocessing import SynchronizedValue
from implicitdict import ImplicitDict


class Database(ImplicitDict):
    """Simple in-memory pseudo-database tracking the state of the mock system"""

    setup_initiated: bool = False
    """True only when a process has already initiated setup"""

    stopping: bool = False
    """True only when the mock_uss should be stopping"""

    cleanup_initiated: bool = False
    """True only when a process has already initiated cleanup"""


db = SynchronizedValue(
    Database(),
    decoder=lambda b: ImplicitDict.parse(json.loads(b.decode("utf-8")), Database),
)
