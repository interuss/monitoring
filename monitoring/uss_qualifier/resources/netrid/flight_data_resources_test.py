import pytest

from monitoring.uss_qualifier.resources.files import ExternalFile

from .flight_data import (
    AdjacentCircularFlightsSimulatorConfiguration,
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
    # accuracy_h is a field in position, speed_accuracy in state.
    for file in [
        "test/invalid_no_accuracy_h.kml",
        "test/invalid_no_speed_accuracy.kml",
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
    FlightDataResource(specs, "test")
