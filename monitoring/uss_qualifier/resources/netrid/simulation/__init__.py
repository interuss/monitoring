from implicitdict import ImplicitDict

from monitoring.monitorlib.geo import LatLngPoint
from monitoring.uss_qualifier.resources.netrid.flight_data import (
    AdjacentCircularFlightsSimulatorConfiguration,
    AdjacentSpiralFlightsSimulatorConfiguration,
    FlightRecordCollection,
)

from .adjacent_circular_flights_simulator import (
    AdjacentCircularFlightsSimulator,
)
from .adjacent_spiral_flights_simulator import (
    AdjacentSpiralFlightsSimulator,
)


def generate_aircraft_states(
    config: AdjacentCircularFlightsSimulatorConfiguration
    | AdjacentSpiralFlightsSimulatorConfiguration,
    allow_duplicate_positions: bool = False,
) -> FlightRecordCollection:
    if isinstance(config, AdjacentSpiralFlightsSimulatorConfiguration):
        my_path_generator = AdjacentSpiralFlightsSimulator(config)
        loop_tracks = False
    else:
        my_path_generator = AdjacentCircularFlightsSimulator(config)
        loop_tracks = True

    my_path_generator.generate_flight_grid_and_path_points(
        altitude_of_ground_level_wgs_84=config.altitude_of_ground_level_wgs_84
    )
    my_path_generator.generate_query_bboxes()

    my_path_generator.generate_rid_state(
        duration=my_path_generator.duration, loop_tracks=loop_tracks
    )
    flights = my_path_generator.flights

    if not allow_duplicate_positions:
        flat_states = []
        for f_idx, flight in enumerate(flights):
            for s_idx, state in enumerate(flight.states):
                if "position" in state and state.position:
                    pt = LatLngPoint(lat=state.position.lat, lng=state.position.lng)
                    flat_states.append((f_idx, s_idx, pt, state))

        for i in range(len(flat_states)):
            f_idx1, s_idx1, pt1, state1 = flat_states[i]
            for j in range(i + 1, len(flat_states)):
                f_idx2, s_idx2, pt2, state2 = flat_states[j]
                if pt1.match(pt2):
                    raise ValueError(
                        f"Duplicate position found: flight {f_idx1} state {s_idx1} at {state1.timestamp} "
                        f"({pt1.lat}, {pt1.lng}) matches flight {f_idx2} state {s_idx2} at {state2.timestamp} "
                        f"({pt2.lat}, {pt2.lng})"
                    )

    result = FlightRecordCollection(flights=flights)
    return ImplicitDict.parse(result, FlightRecordCollection)
