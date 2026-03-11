import unittest

from s2sphere import LatLng

from monitoring.monitorlib.geo import (
    Altitude,
    AltitudeDatum,
    Circle,
    DistanceUnits,
    LatLngPoint,
    Polygon,
    Radius,
    Volume3D,
    generate_area_in_vicinity,
    generate_slight_overlap_area,
)

MAX_DIFFERENCE = 0.001


def _points(in_points: list[tuple[float, float]]) -> list[LatLng]:
    return [LatLng.from_degrees(*p) for p in in_points]


class AltitudeIsEquivalentTest(unittest.TestCase):
    def setUp(self):
        self.alt1 = Altitude(
            value=100, reference=AltitudeDatum.W84, units=DistanceUnits.M
        )

    def test_equivalent_altitudes(self):
        alt2 = Altitude(value=100, reference=AltitudeDatum.W84, units=DistanceUnits.M)
        self.assertTrue(self.alt1.is_equivalent(alt2))

    def test_equivalent_altitudes_within_tolerance(self):
        alt2 = Altitude(
            value=100.000001, reference=AltitudeDatum.W84, units=DistanceUnits.M
        )
        self.assertTrue(self.alt1.is_equivalent(alt2))

    def test_equivalent_altitudes_different_units(self):
        alt2 = Altitude(
            value=328.084, reference=AltitudeDatum.W84, units=DistanceUnits.FT
        )
        self.assertTrue(self.alt1.is_equivalent(alt2))

    def test_nonequivalent_altitudes_different_value(self):
        alt2 = Altitude(value=101, reference=AltitudeDatum.W84, units=DistanceUnits.M)
        self.assertFalse(self.alt1.is_equivalent(alt2))

    def test_nonequivalent_altitudes_different_reference(self):
        alt2 = Altitude(value=100, reference=AltitudeDatum.SFC, units=DistanceUnits.M)
        self.assertFalse(self.alt1.is_equivalent(alt2))


class PolygonIsEquivalentTest(unittest.TestCase):
    def setUp(self):
        self.poly1 = Polygon(
            vertices=[
                LatLngPoint(lat=10, lng=10),
                LatLngPoint(lat=11, lng=10),
                LatLngPoint(lat=11, lng=11),
                LatLngPoint(lat=10, lng=11),
            ]
        )

    def test_equivalent_polygons(self):
        poly2 = Polygon(
            vertices=[
                LatLngPoint(lat=10, lng=10),
                LatLngPoint(lat=11, lng=10),
                LatLngPoint(lat=11, lng=11),
                LatLngPoint(lat=10, lng=11),
            ]
        )
        self.assertTrue(self.poly1.is_equivalent(poly2))

    def test_equivalent_polygons_within_tolerance(self):
        poly2 = Polygon(
            vertices=[
                LatLngPoint(lat=10.00000001, lng=10.00000001),
                LatLngPoint(lat=11.00000001, lng=10.00000001),
                LatLngPoint(lat=11.00000001, lng=11.00000001),
                LatLngPoint(lat=10.00000001, lng=11.00000001),
            ]
        )
        self.assertTrue(self.poly1.is_equivalent(poly2))

    def test_nonequivalent_polygons(self):
        poly2 = Polygon(
            vertices=[
                LatLngPoint(lat=10, lng=10),
                LatLngPoint(lat=12, lng=10),
                LatLngPoint(lat=12, lng=11),
                LatLngPoint(lat=10, lng=11),
            ]
        )
        self.assertFalse(self.poly1.is_equivalent(poly2))

    def test_equivalent_polygons_none(self):
        poly1 = Polygon(vertices=None)
        poly2 = Polygon(vertices=None)
        self.assertTrue(poly1.is_equivalent(poly2))

    def test_nonequivalent_polygons_one_none(self):
        poly1 = Polygon(vertices=[])
        poly2 = Polygon(vertices=None)
        self.assertFalse(poly1.is_equivalent(poly2))


class Volume3DIsEquivalentTest(unittest.TestCase):
    def setUp(self):
        self.vol_poly = Volume3D(
            outline_polygon=Polygon(
                vertices=[
                    LatLngPoint(lat=10, lng=10),
                    LatLngPoint(lat=11, lng=10),
                    LatLngPoint(lat=11, lng=11),
                    LatLngPoint(lat=10, lng=11),
                ]
            ),
            altitude_lower=Altitude(
                value=100, reference=AltitudeDatum.W84, units=DistanceUnits.M
            ),
            altitude_upper=Altitude(
                value=200, reference=AltitudeDatum.W84, units=DistanceUnits.M
            ),
        )
        self.vol_circle = Volume3D(
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

    def test_equivalent_volumes_polygon(self):
        vol2 = Volume3D(
            outline_polygon=Polygon(
                vertices=[
                    LatLngPoint(lat=10, lng=10),
                    LatLngPoint(lat=11, lng=10),
                    LatLngPoint(lat=11, lng=11),
                    LatLngPoint(lat=10, lng=11),
                ]
            ),
            altitude_lower=Altitude(
                value=100, reference=AltitudeDatum.W84, units=DistanceUnits.M
            ),
            altitude_upper=Altitude(
                value=200, reference=AltitudeDatum.W84, units=DistanceUnits.M
            ),
        )
        self.assertTrue(self.vol_poly.is_equivalent(vol2))

    def test_equivalent_volumes_circle(self):
        vol2 = Volume3D(
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
        self.assertTrue(self.vol_circle.is_equivalent(vol2))

    def test_nonequivalent_volumes_circle(self):
        vol2 = Volume3D(
            outline_circle=Circle(
                center=LatLngPoint(lat=10, lng=10),
                radius=Radius(value=200, units=DistanceUnits.M),
            ),
            altitude_lower=Altitude(
                value=100, reference=AltitudeDatum.W84, units=DistanceUnits.M
            ),
            altitude_upper=Altitude(
                value=200, reference=AltitudeDatum.W84, units=DistanceUnits.M
            ),
        )
        self.assertFalse(self.vol_circle.is_equivalent(vol2))

    def test_nonequivalent_volumes_different_shape(self):
        vol2 = Volume3D(
            outline_circle=Circle(
                center=LatLngPoint(lat=10.5, lng=10.5),
                radius=Radius(value=50000, units=DistanceUnits.M),
            )
        )
        self.assertFalse(self.vol_poly.is_equivalent(vol2))

    def test_equivalent_volumes_none_fields(self):
        vol1 = Volume3D()
        vol2 = Volume3D()
        self.assertTrue(vol1.is_equivalent(vol2))

    def test_nonequivalent_volumes_one_none_field(self):
        vol1 = Volume3D(
            altitude_lower=Altitude(
                value=100, reference=AltitudeDatum.W84, units=DistanceUnits.M
            )
        )
        vol2 = Volume3D()
        self.assertFalse(vol1.is_equivalent(vol2))


def test_generate_slight_overlap_area():
    # Square around 0,0 of edge length 2 -> first corner at 1,1 -> expect a square with overlapping corner at 1,1
    assert generate_slight_overlap_area(
        _points([(1, 1), (1, -1), (-1, -1), (-1, 1)])
    ) == _points([(1, 1), (1, 2), (2, 2), (2, 1)])

    # Square with diagonal from 0,0 to 1,1 -> first corner at 1,1 -> expect a square with overlapping corner at 1,1
    assert generate_slight_overlap_area(
        _points([(1, 1), (0, 1), (0, 0), (1, 0)])
    ) == _points([(1, 1), (1, 1.5), (1.5, 1.5), (1.5, 1)])

    # Square with diagonal from 0,0 to -1,-1 -> first corner at -1,-1 -> expect a square with overlapping corner at -1,-1
    assert generate_slight_overlap_area(
        _points([(-1, -1), (0, -1), (0, 0), (-1, 0)])
    ) == _points([(-1, -1), (-1, -1.5), (-1.5, -1.5), (-1.5, -1)])

    # Square with diagonal from 0,0 to -1,1 -> first corner at -1,1 -> expect a square with overlapping corner at -1,0
    assert generate_slight_overlap_area(
        _points([(-1, 1), (-1, 0), (0, 0), (0, 1)])
    ) == _points([(-1, 1), (-1, 1.5), (-1.5, 1.5), (-1.5, 1)])

    # Square with diagonal from 0,0 to 1,-1 -> first corner at 1,-1 -> expect a square with overlapping corner at 1,-1
    assert generate_slight_overlap_area(
        _points([(1, -1), (1, 0), (0, 0), (0, -1)])
    ) == _points([(1, -1), (1, -1.5), (1.5, -1.5), (1.5, -1)])


def _approx_equals(p1: list[LatLng], p2: list[LatLng]) -> bool:
    return all([p1[i].approx_equals(p2[i], MAX_DIFFERENCE) for i in range(len(p1))])


def test_generate_area_in_vicinity():
    # Square around 0,0 of edge length 2 -> first corner at 1,1. rel_distance of 2:
    # expect a 1 by 1 square with the closest corner at 3,3
    assert _approx_equals(
        generate_area_in_vicinity(_points([(1, 1), (1, -1), (-1, -1), (-1, 1)]), 2),
        _points([(3.0, 3.0), (3.0, 4.0), (4.0, 4.0), (4.0, 3.0)]),
    )

    # Square around 0,0 of edge length 2 -> first corner at 1,-1. rel_distance of 2:
    # expect a 1 by 1 square with the closest corner at 3,-3
    assert _approx_equals(
        generate_area_in_vicinity(_points([(1, -1), (-1, -1), (-1, 1), (1, 1)]), 2),
        _points([(3.0, -3.0), (3.0, -4.0), (4.0, -4.0), (4.0, -3.0)]),
    )

    # Square with diagonal from 0,0 to -1,-1 -> first corner at -1,-1. rel_distance of 2:
    # expect a .5 by .5 square with the closest corner at -2,-2
    assert _approx_equals(
        generate_area_in_vicinity(_points([(-1, -1), (0, -1), (0, 0), (-1, 0)]), 2),
        _points([(-2.0, -2.0), (-2.0, -2.5), (-2.5, -2.5), (-2.5, -2.0)]),
    )
