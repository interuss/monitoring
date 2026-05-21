import unittest
from datetime import datetime, timedelta

from monitoring.monitorlib.geo import (
    Altitude,
    AltitudeDatum,
    Circle,
    DistanceUnits,
    LatLngPoint,
    Radius,
    Volume3D,
)
from monitoring.monitorlib.geotemporal import Volume4D, Volume4DCollection
from monitoring.monitorlib.temporal import Time


class Volume4DIsEquivalentTest(unittest.TestCase):
    def setUp(self):
        self.t0 = datetime.now()
        self.t1 = self.t0 + timedelta(minutes=10)
        self.vol_3d = Volume3D(
            outline_circle=Circle(
                center=LatLngPoint(lat=10, lng=10),
                radius=Radius(value=100, units=DistanceUnits.M),
            ),
            altitude_lower=Altitude(
                value=100, reference=AltitudeDatum.W84, units=DistanceUnits.M
            ),
            altitude_upper=Altitude(
                value=200, reference=AltitudeDatum.W84, units=DistanceUnits.M
            ),
        )
        self.vol1 = Volume4D(
            volume=self.vol_3d,
            time_start=Time(self.t0),
            time_end=Time(self.t1),
        )

    def test_equivalent_volume4d(self):
        vol2 = Volume4D(
            volume=self.vol_3d,
            time_start=Time(self.t0),
            time_end=Time(self.t1),
        )
        self.assertTrue(self.vol1.is_equivalent(vol2))

    def test_equivalent_volume4d_within_tolerance(self):
        # Time within tolerance (default is 10ms)
        vol2 = Volume4D(
            volume=self.vol_3d,
            time_start=Time(self.t0 + timedelta(milliseconds=3)),
            time_end=Time(self.t1 - timedelta(milliseconds=3)),
        )
        self.assertTrue(self.vol1.is_equivalent(vol2))

    def test_nonequivalent_volume4d_time_outside_tolerance(self):
        vol2 = Volume4D(
            volume=self.vol_3d,
            time_start=Time(self.t0 + timedelta(seconds=2)),
            time_end=Time(self.t1),
        )
        self.assertFalse(self.vol1.is_equivalent(vol2))

    def test_nonequivalent_volume4d_different_volume3d(self):
        vol2 = Volume4D(
            volume=Volume3D(
                outline_circle=Circle(
                    center=LatLngPoint(lat=10, lng=10),
                    radius=Radius(value=200, units=DistanceUnits.M),
                ),
                altitude_lower=self.vol_3d.altitude_lower,
                altitude_upper=self.vol_3d.altitude_upper,
            ),
            time_start=Time(self.t0),
            time_end=Time(self.t1),
        )
        self.assertFalse(self.vol1.is_equivalent(vol2))

    def test_equivalent_volume4d_none_times(self):
        vol1_no_time = Volume4D(volume=self.vol_3d)
        vol2_no_time = Volume4D(volume=self.vol_3d)
        self.assertTrue(vol1_no_time.is_equivalent(vol2_no_time))

    def test_nonequivalent_volume4d_one_none_time(self):
        vol2 = Volume4D(volume=self.vol_3d, time_start=Time(self.t0))
        self.assertFalse(self.vol1.is_equivalent(vol2))


class Volume4DCollectionIsEquivalentTest(unittest.TestCase):
    def setUp(self):
        self.t0 = datetime.now()
        self.v1 = Volume4D(
            volume=Volume3D(
                outline_circle=Circle(
                    center=LatLngPoint(lat=10, lng=10),
                    radius=Radius(value=100, units=DistanceUnits.M),
                )
            ),
            time_start=Time(self.t0),
        )
        self.v2 = Volume4D(
            volume=Volume3D(
                outline_circle=Circle(
                    center=LatLngPoint(lat=20, lng=20),
                    radius=Radius(value=200, units=DistanceUnits.M),
                )
            ),
            time_start=Time(self.t0),
        )
        self.v3 = Volume4D(
            volume=Volume3D(
                outline_circle=Circle(
                    center=LatLngPoint(lat=30, lng=30),
                    radius=Radius(value=300, units=DistanceUnits.M),
                )
            ),
            time_start=Time(self.t0),
        )

    def test_equivalent_collection_same_order(self):
        c1 = Volume4DCollection([self.v1, self.v2])
        c2 = Volume4DCollection([self.v1, self.v2])
        self.assertTrue(c1.is_equivalent(c2))

    def test_equivalent_collection_different_order(self):
        c1 = Volume4DCollection([self.v1, self.v2])
        c2 = Volume4DCollection([self.v2, self.v1])
        self.assertTrue(c1.is_equivalent(c2))

    def test_nonequivalent_collection_different_lengths(self):
        c1 = Volume4DCollection([self.v1])
        c2 = Volume4DCollection([])
        self.assertFalse(c1.is_equivalent(c2))

    def test_nonequivalent_collection_different_content(self):
        c1 = Volume4DCollection([self.v1, self.v2])
        c2 = Volume4DCollection([self.v1, self.v3])
        self.assertFalse(c1.is_equivalent(c2))
