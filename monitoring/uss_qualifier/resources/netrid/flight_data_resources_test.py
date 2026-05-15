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
    FlightDataResource(specs, "test")
