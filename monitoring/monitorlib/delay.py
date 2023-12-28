from datetime import timedelta
import time
from typing import Union

from loguru import logger


MAX_SILENT_DELAY_S = 0.4
"""Number of seconds to delay above which a reasoning message should be displayed."""


def sleep(duration: Union[float, timedelta], reason: str) -> None:
    """Sleep for the specified amount of time, logging the fact that the delay is occurring (when appropriate).

    Args:
        duration: Amount of time to sleep for; interpreted as seconds if float.
        reason: Reason the delay is happening (to be printed to console/log if appropriate).
    """
    if isinstance(duration, timedelta):
        duration = duration.total_seconds()
    if duration <= 0:
        # No need to delay
        return

    if duration > MAX_SILENT_DELAY_S:
        logger.debug(f"Delaying {duration:.1f} seconds because {reason}")
    time.sleep(duration)
