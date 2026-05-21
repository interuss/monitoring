import json
from collections.abc import Callable
from datetime import UTC, datetime

import arrow
from implicitdict import ImplicitDict

from monitoring.mock_uss.flights.database import (
    DEADLOCK_TIMEOUT,
    FlightRecord,
    MockUSSFlightID,
    db,
)
from monitoring.monitorlib.clients.flight_planning.flight_info import FlightInfo
from monitoring.monitorlib.delay import sleep
from monitoring.monitorlib.temporal import Time


def adjust_flight_info(info: FlightInfo) -> FlightInfo:
    result: FlightInfo = ImplicitDict.parse(json.loads(json.dumps(info)), FlightInfo)

    now = arrow.utcnow()

    for v4d in result.basic_information.area:
        # Fill in empty start times with now
        if "time_start" not in v4d or not v4d.time_start:
            v4d.time_start = Time(now)

        # Truncate volume start times to current
        elif v4d.time_start.datetime < now:
            v4d.time_start = Time(now)

    # Validate volume times
    for i, v4d in enumerate(result.basic_information.area):
        if (
            "time_start" in v4d
            and v4d.time_start
            and "time_end" in v4d
            and v4d.time_end
            and v4d.time_start >= v4d.time_end
        ):
            raise ValueError(
                f"Volume {i} start time {v4d.time_start} (originally {info.basic_information.area[i].time_start}) is at or after end time {v4d.time_end}"
            )

    return result


def lock_flight(flight_id: MockUSSFlightID, log: Callable[[str], None]) -> FlightRecord:
    # If this is a change to an existing flight, acquire lock to that flight
    log(f"Acquiring lock for flight {flight_id}")
    deadline = datetime.now(UTC) + DEADLOCK_TIMEOUT
    while True:
        with db.transact() as tx:
            if flight_id in tx.value.flights:
                # This is an existing flight being modified
                existing_flight = tx.value.flights[flight_id]
                if existing_flight and not existing_flight.locked:
                    log("Existing flight locked for update")
                    existing_flight.locked = True
                    break
            else:
                log("Request is for a new flight (lock established)")
                tx.value.flights[flight_id] = None
                existing_flight = None
                break
        # We found an existing flight but it was locked; wait for it to become
        # available
        sleep(0.5, f"flight {flight_id} is currently already locked")

        if datetime.now(UTC) > deadline:
            raise RuntimeError(
                f"Deadlock in inject_flight while attempting to gain access to flight {flight_id}"
            )
    return existing_flight


def release_flight_lock(flight_id: MockUSSFlightID, log: Callable[[str], None]) -> None:
    with db.transact() as tx:
        if flight_id in tx.value.flights:
            flight = tx.value.flights[flight_id]
            if flight:
                # FlightRecord was a true existing flight
                log(f"Releasing lock on existing flight_id {flight_id}")
                flight.locked = False
            else:
                # FlightRecord was just a placeholder for a new flight
                log(f"Releasing placeholder for existing flight_id {flight_id}")
                del tx.value.flights[flight_id]


def delete_flight_record(flight_id: MockUSSFlightID) -> FlightRecord | None:
    deadline = datetime.now(UTC) + DEADLOCK_TIMEOUT
    while True:
        with db.transact() as tx:
            if flight_id in tx.value.flights:
                flight = tx.value.flights[flight_id]
                if flight and not flight.locked:
                    # FlightRecord was a true existing flight not being mutated anywhere else
                    del tx.value.flights[flight_id]
                    return flight
            else:
                # No FlightRecord found
                return None
        # There is a race condition with another handler to create or modify the requested flight; wait for that to resolve
        sleep(
            0.5,
            f"flight {flight_id} is currently already locked while we are trying to delete it",
        )
        if datetime.now(UTC) > deadline:
            raise RuntimeError(
                f"Deadlock in delete_flight while attempting to gain access to flight {flight_id} (now: {datetime.now(UTC)}, deadline: {deadline})"
            )
