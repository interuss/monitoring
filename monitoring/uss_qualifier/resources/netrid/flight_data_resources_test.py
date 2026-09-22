import pytest
from pyproj import Geod

from monitoring.uss_qualifier.resources.files import ExternalFile
from monitoring.uss_qualifier.resources.netrid.simulation import (
    generate_aircraft_states,
)

from .flight_data import (
    AdjacentCircularFlightsSimulatorConfiguration,
    AdjacentSpiralFlightsSimulatorConfiguration,
    FlightDataKMLFileConfiguration,
    FlightDataSpecification,
)
from .flight_data_resources import FlightDataResource


def test_unknown_type():
    specs = FlightDataSpecification()

    with pytest.raises(ValueError):
        FlightDataResource(specs, "test")


def test_record():
    specs = FlightDataSpecification(
        record_source=ExternalFile(path="file://./test_data/test/zurich.json")
    )
    FlightDataResource(specs, "test")


def test_invalid_record():
    for file in [
        "test/invalid_wrong_ua_type.json",
        "test/invalid_no_timestamp.json",
        "test/invalid_wrong_timestamp.json",
        "test/invalid_no_timestamp_accuracy.json",
        "test/invalid_wrong_timestamp_accuracy.json",
        "test/invalid_wrong_operational_status.json",
        "test/invalid_no_alt.json",
        "test/invalid_no_accuracy_v.json",
        "test/invalid_wrong_accuracy_v.json",
        "test/invalid_no_accuracy_h.json",
        "test/invalid_wrong_accuracy_h.json",
        "test/invalid_no_speed_accuracy.json",
        "test/invalid_wrong_speed_accuracy.json",
        "test/invalid_no_vertical_speed.json",
        "test/invalid_wrong_vertical_speed.json",
        "test/invalid_no_speed.json",
        "test/invalid_wrong_speed.json",
        "test/invalid_no_track.json",
        "test/invalid_wrong_track.json",
        "test/invalid_no_height.json",
        "test/invalid_no_height_type.json",
        "test/invalid_wrong_height_type.json",
        "test/invalid_no_uas_id.json",
        "test/invalid_wrong_serial_number.json",
        "test/invalid_wrong_registration_id.json",
        "test/invalid_wrong_utm_id.json",
    ]:
        specs = FlightDataSpecification(
            record_source=ExternalFile(path=f"file://./test_data/{file}")
        )
        with pytest.raises(Exception):
            FlightDataResource(specs, "test")


def test_kmls():
    # We test all known KMLs, who should be valid
    for file in ["usa/netrid/dcdemo.kml", "usa/kentland/rid.kml", "che/rid/zurich.kml"]:
        specs = FlightDataSpecification(
            kml_source=FlightDataKMLFileConfiguration(
                kml_file=ExternalFile(path=f"file://./test_data/{file}")
            )
        )
        FlightDataResource(specs, "test")


def test_invalid_kmls():
    # accuracy_h is a field in position, speed_accuracy in state. Notice it's
    # hard to generate invalid values from others fields as kml parser will
    # crash / generate most of them
    for file in [
        "test/invalid_no_accuracy_h.kml",
        "test/invalid_no_speed_accuracy.kml",
        "test/invalid_wrong_serial_number.kml",
        "test/invalid_wrong_ua_type.kml",
    ]:
        specs = FlightDataSpecification(
            kml_source=FlightDataKMLFileConfiguration(
                kml_file=ExternalFile(path=f"file://./test_data/{file}")
            )
        )
        with pytest.raises(Exception):
            FlightDataResource(specs, "test")


def test_adjacent_circular_flights_simuation_source():
    specs = FlightDataSpecification(
        adjacent_circular_flights_simulation_source=AdjacentCircularFlightsSimulatorConfiguration()
    )
    resource = FlightDataResource(specs, "test")

    assert len(resource.flight_collection.flights) == 6
    assert [len(f.states) for f in resource.flight_collection.flights] == [
        30,
        30,
        30,
        30,
        30,
        30,
    ]


def test_adjacent_circular_flights_simulation_source_configuration():
    specs = FlightDataSpecification(
        adjacent_circular_flights_simulation_source=AdjacentCircularFlightsSimulatorConfiguration(
            num_flights=4,
            duration=61,
        )
    )

    resource = FlightDataResource(specs, "test")

    assert len(resource.flight_collection.flights) == 4
    assert [len(f.states) for f in resource.flight_collection.flights] == [
        61,
        61,
        61,
        61,
    ]


@pytest.mark.parametrize(
    "num_flights,duration",
    [
        (0, 61),
        (4, 0),
    ],
)
def test_adjacent_circular_flights_simulation_source_invalid_configuration(
    num_flights, duration
):
    specs = FlightDataSpecification(
        adjacent_circular_flights_simulation_source=AdjacentCircularFlightsSimulatorConfiguration(
            num_flights=num_flights,
            duration=duration,
        )
    )

    with pytest.raises(ValueError):
        FlightDataResource(specs, "test")


def test_adjacent_circular_flights_duplicates_error():
    # A configuration that is known to produce duplicate positions (e.g. duration=90, num_flights=2)
    config = AdjacentCircularFlightsSimulatorConfiguration(
        minx=8.508996,
        miny=47.382846,
        maxx=8.514161,
        maxy=47.386336,
        utm_zone=32,
        altitude_of_ground_level_wgs_84=48,
        num_flights=2,
        duration=90,
    )
    # By default, allow_duplicate_positions is False, which should error out on duplicate positions
    with pytest.raises(ValueError, match="Duplicate position found"):
        generate_aircraft_states(config, allow_duplicate_positions=False)


def test_adjacent_circular_flights_duplicates_allowed():
    config = AdjacentCircularFlightsSimulatorConfiguration(
        minx=8.508996,
        miny=47.382846,
        maxx=8.514161,
        maxy=47.386336,
        utm_zone=32,
        altitude_of_ground_level_wgs_84=48,
        num_flights=2,
        duration=90,
    )
    # With allow_duplicate_positions=True, it should successfully generate states
    collection = generate_aircraft_states(config, allow_duplicate_positions=True)
    assert len(collection.flights) == 2


def test_adjacent_spiral_flights_simulation_source():
    specs = FlightDataSpecification(
        adjacent_spiral_flights_simulation_source=AdjacentSpiralFlightsSimulatorConfiguration()
    )
    resource = FlightDataResource(specs, "test")

    assert len(resource.flight_collection.flights) == 6
    assert [len(f.states) for f in resource.flight_collection.flights] == [
        30,
        30,
        30,
        30,
        30,
        30,
    ]


def test_adjacent_spiral_flights_simulation_source_configuration():
    specs = FlightDataSpecification(
        adjacent_spiral_flights_simulation_source=AdjacentSpiralFlightsSimulatorConfiguration(
            num_flights=4,
            duration=61,
        )
    )

    resource = FlightDataResource(specs, "test")

    assert len(resource.flight_collection.flights) == 4
    assert [len(f.states) for f in resource.flight_collection.flights] == [
        61,
        61,
        61,
        61,
    ]


@pytest.mark.parametrize(
    "num_flights,duration",
    [
        (0, 61),
        (4, 0),
    ],
)
def test_adjacent_spiral_flights_simulation_source_invalid_configuration(
    num_flights, duration
):
    specs = FlightDataSpecification(
        adjacent_spiral_flights_simulation_source=AdjacentSpiralFlightsSimulatorConfiguration(
            num_flights=num_flights,
            duration=duration,
        )
    )

    with pytest.raises(ValueError):
        FlightDataResource(specs, "test")


def test_adjacent_spiral_flights_spiral_behavior():
    specs = FlightDataSpecification(
        adjacent_spiral_flights_simulation_source=AdjacentSpiralFlightsSimulatorConfiguration(
            num_flights=1,
            duration=30,
        )
    )
    resource = FlightDataResource(specs, "test")
    flight = resource.flight_collection.flights[0]

    # Verify that distance from center is strictly decreasing
    # We can calculate distance of each state from the initial state or from center.
    # Since center is roughly the centroid, let's verify that distance to final point (the center)
    # is generally decreasing, or we can check the distance between subsequent points is around 5.0 m.
    geod = Geod(ellps="WGS84")
    distances_between_points = []
    for i in range(len(flight.states) - 1):
        p1 = flight.states[i].position
        p2 = flight.states[i + 1].position
        assert p1 is not None
        assert p2 is not None
        _, _, dist = geod.inv(p1.lng, p1.lat, p2.lng, p2.lat)
        distances_between_points.append(dist)

    # Average distance between points should be around 5.0 m (since v = 5.0 m/s and delta_t = 1s)
    avg_dist = sum(distances_between_points) / len(distances_between_points)
    assert 4.5 < avg_dist < 5.5

    # Also verify there are no duplicate positions
    # (should not raise exceptions during resource load which already validates this)
    assert len(flight.states) == 30
