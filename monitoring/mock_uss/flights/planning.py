from collections.abc import Callable
from datetime import UTC, datetime

from monitoring.mock_uss.flights.database import DEADLOCK_TIMEOUT, FlightRecord, db
from monitoring.monitorlib.delay import sleep


def lock_flight(flight_id: str, log: Callable[[str], None]) -> FlightRecord:
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


def release_flight_lock(flight_id: str, log: Callable[[str], None]) -> None:
    with db.transact() as tx:
        if flight_id in tx.value.flights:
            if tx.value.flights[flight_id]:
                # FlightRecord was a true existing flight
                log(f"Releasing lock on existing flight_id {flight_id}")
                tx.value.flights[flight_id].locked = False
            else:
                # FlightRecord was just a placeholder for a new flight
                log(f"Releasing placeholder for existing flight_id {flight_id}")
                del tx.value.flights[flight_id]


def delete_flight_record(flight_id: str) -> FlightRecord | None:
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
