import math

from shapely.geometry import Point

from monitoring.uss_qualifier.resources.netrid.flight_data import (
    AdjacentSpiralFlightsSimulatorConfiguration,
)
from monitoring.uss_qualifier.resources.netrid.simulation.adjacent_circular_flights_simulator import (
    AdjacentCircularFlightsSimulator,
)

from .utils import FlightPoint, GridCellFlight


class AdjacentSpiralFlightsSimulator(AdjacentCircularFlightsSimulator):
    """A class to generate Flight Paths as inwards spirals given a bounding box.

    It inherits from AdjacentCircularFlightsSimulator to reuse bounding box,
    UTM conversion, and details generation logic.
    """

    def __init__(self, config: AdjacentSpiralFlightsSimulatorConfiguration) -> None:
        super().__init__(config)

    def generate_flight_grid_and_path_points(
        self, altitude_of_ground_level_wgs_84: float
    ):
        """Generate a series of boxes (grid) within the given bounding box and inward spiral tracks inside each cell."""
        grid_cells = self.generate_grid_cells()

        all_grid_cell_tracks = []

        R_outer = 50.0
        R_inner = 10.0
        v = 5.0  # constant speed in m/s (equivalent to circular flight speed)
        D = self.duration
        a = (R_outer - R_inner) / D

        # Iterate over the flight_grid
        for grid_cell in grid_cells:
            center = grid_cell.centroid
            center_utm = self.utm_converter(center)
            assert isinstance(center_utm, Point)

            altitude = (
                altitude_of_ground_level_wgs_84 + self.altitude_agl
            )  # meters WGS 84

            # Generate D + 1 UTM coordinates
            utm_points = []
            for t in range(D + 1):
                r_t = R_outer - a * t
                r_t = max(R_inner, r_t)
                theta_t = -(v / a) * math.log(r_t / R_outer)
                x_t = center_utm.x + r_t * math.cos(theta_t)
                y_t = center_utm.y + r_t * math.sin(theta_t)
                utm_points.append(Point(x_t, y_t))

            # Convert UTM points to WGS84
            wgs84_points = [self.utm_converter(pt, inverse=True) for pt in utm_points]

            flight_points_with_altitude = []
            for t in range(D):
                pt_curr = wgs84_points[t]
                pt_next = wgs84_points[t + 1]

                adjacent_points = [pt_curr, pt_next]
                flight_speed, bearing = self.generate_flight_speed_bearing(
                    adjacent_points=adjacent_points, delta_time_secs=1
                )

                assert isinstance(pt_curr, Point)
                flight_points_with_altitude.append(
                    FlightPoint(
                        lat=pt_curr.y,
                        lng=pt_curr.x,
                        alt=altitude,
                        speed=flight_speed,
                        bearing=bearing,
                    )
                )

            all_grid_cell_tracks.append(
                GridCellFlight(bounds=grid_cell, track=flight_points_with_altitude)
            )

        self.grid_cells_flight_tracks = all_grid_cell_tracks
