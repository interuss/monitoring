from datetime import timedelta
import json
from typing import Dict

from monitoring.mock_uss.tracer.observation_areas import (
    ObservationAreaID,
    ObservationArea,
)
from monitoring.monitorlib.multiprocessing import SynchronizedValue
from implicitdict import ImplicitDict, StringBasedTimeDelta


class Database(ImplicitDict):
    """Simple in-memory pseudo-database tracking the state of the mock system"""

    setup_initiated: bool = False
    """True only when a process has already initiated setup"""

    stopping: bool = False
    """True only when the mock_uss should be stopping"""

    cleanup_initiated: bool = False
    """True only when a process has already initiated cleanup"""

    observation_areas: Dict[ObservationAreaID, ObservationArea]
    """Set of active observation areas, keyed by ID"""

    polling_interval: StringBasedTimeDelta = StringBasedTimeDelta(timedelta(seconds=15))
    """Interval at which polling of observation areas should occur"""


db = SynchronizedValue(
    Database(observation_areas={}),
    decoder=lambda b: ImplicitDict.parse(json.loads(b.decode("utf-8")), Database),
)
