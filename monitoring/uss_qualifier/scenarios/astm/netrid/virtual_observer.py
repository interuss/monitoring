import time
from datetime import timedelta, datetime
from typing import Optional, Callable, List
from loguru import logger

import arrow
from s2sphere import LatLngRect

from monitoring.uss_qualifier.scenarios.astm.netrid.injected_flight_collection import (
    InjectedFlightCollection,
)


class VirtualObserver(object):
    """Defines the behavior of a virtual human-like observer.

    The observer wants to look at the specified collection of flights, and this
    class indicates their behavior by computing the query rectangle at each
    polling instance.
    """

    _injected_flights: InjectedFlightCollection
    """Set of flights this virtual observer is going to observe"""

    _repeat_query_rect_period: int
    """If set to a value above zero, reuse the most recent query rectangle/view every this many queries."""

    _min_query_diagonal_m: float
    """Do not make queries with diagonals smaller than this many meters."""

    _relevant_past_data_period: timedelta
    """Length of time prior to a query that may contain relevant observable data"""

    _repeat_query_counter: int = 0
    """Number of repeated queries to the same rectangle; related to _repeat_query_rect_period"""

    _last_rect: Optional[LatLngRect] = None
    """The most recent query rectangle"""

    def __init__(
        self,
        injected_flights: InjectedFlightCollection,
        repeat_query_rect_period: int,
        min_query_diagonal_m: float,
        relevant_past_data_period: timedelta,
    ):
        self._injected_flights = injected_flights
        self._repeat_query_rect_period = repeat_query_rect_period
        self._min_query_diagonal_m = min_query_diagonal_m
        self._relevant_past_data_period = relevant_past_data_period

    def get_query_rect(self, diagonal_m: float = None) -> LatLngRect:
        if not diagonal_m or diagonal_m < self._min_query_diagonal_m:
            diagonal_m = self._min_query_diagonal_m
        t_now = arrow.utcnow().datetime
        if (
            self._last_rect
            and self._repeat_query_rect_period > 0
            and self._repeat_query_counter >= self._repeat_query_rect_period == 0
        ):
            rect = self._last_rect
        else:
            t_min = t_now - self._relevant_past_data_period
            rect = self._injected_flights.get_query_rect(t_min, t_now, diagonal_m)
            self._last_rect = rect
        return rect

    def get_last_time_of_interest(self) -> datetime:
        """Return the time after which there will be no data of interest to this observer."""
        return (
            self._injected_flights.get_end_of_injected_data()
            + self._relevant_past_data_period
        )

    def start_polling(
        self,
        interval: timedelta,
        diagonals_m: List[float],
        poll_fct: Callable[[LatLngRect], bool],
    ) -> None:
        """
        Start polling of the RID system.

        :param interval: polling interval.
        :param diagonals_m: list of the query rectangle diagonals (in meters).
        :param poll_fct: polling function to invoke. If it returns True, the polling will be immediately interrupted before the end.
        """
        t_end = self.get_last_time_of_interest()
        t_now = arrow.utcnow()
        if t_now > t_end:
            raise ValueError(
                f"Cannot poll RID system: instructed to poll until {t_end}, which is before now ({t_now})"
            )

        logger.info(f"Polling from {t_now} until {t_end} every {interval}")
        t_next = arrow.utcnow()
        while arrow.utcnow() < t_end:
            interrupt_polling = False
            for diagonal_m in diagonals_m:
                rect = self.get_query_rect(diagonal_m)
                interrupt_polling = poll_fct(rect)
                if interrupt_polling:
                    break

            if interrupt_polling:
                logger.info(f"Polling ended early at {arrow.utcnow()}.")
                break

            # Wait until minimum polling interval elapses
            while t_next < arrow.utcnow():
                t_next += interval
            if t_next > t_end:
                logger.info(f"Polling ended normally at {t_end}.")
                break
            delay = t_next - arrow.utcnow()
            if delay.total_seconds() > 0:
                logger.debug(
                    f"Waiting {delay.total_seconds()} seconds before polling RID system again..."
                )
                time.sleep(delay.total_seconds())
