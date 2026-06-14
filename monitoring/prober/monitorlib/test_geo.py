import s2sphere

from monitoring.monitorlib import geo


def test_flatten_unflatten():
    pts = [(34, -118), (-70, -150), (45, 9), (-10, 80), (0, 0), (1, 1), (-1, -1)]
    deltas = [(0, 0), (1e-6, 1e-6), (1e-3, 1e-3), (-1e-2, 1e-2), (1e-4, -1e-4)]

    for pt in pts:
        ref = s2sphere.LatLng.from_degrees(pt[0], pt[1])
        for delta in deltas:
            p = s2sphere.LatLng.from_degrees(pt[0] + delta[0], pt[1] + delta[1])
            xy = geo.flatten(ref, p)
            p1 = geo.unflatten(ref, xy)
            assert abs(p.lat().degrees - p1.lat().degrees) < 1e-9
            assert abs(p.lng().degrees - p1.lng().degrees) < 1e-9


def test_rotation_translation():
    p_ref = s2sphere.LatLng.from_degrees(45.0, 9.0)
    p_tgt = s2sphere.LatLng.from_degrees(46.0, 10.0)

    r_matrix = geo.make_rotation_matrix(p_ref, p_tgt)

    p_ref_rotated = geo.apply_rotation(r_matrix, p_ref)
    assert abs(p_ref_rotated.lat().degrees - p_tgt.lat().degrees) < 1e-9
    assert abs(p_ref_rotated.lng().degrees - p_tgt.lng().degrees) < 1e-9

    from monitoring.monitorlib.geo import LatLngPoint, Polygon, Volume3D
    from monitoring.monitorlib.transformations import (
        AbsoluteTranslation,
        RelativeTranslation,
    )

    poly = Polygon(
        vertices=[
            LatLngPoint(lat=45.0, lng=9.0),
            LatLngPoint(lat=45.1, lng=9.0),
            LatLngPoint(lat=45.1, lng=9.1),
            LatLngPoint(lat=45.0, lng=9.1),
        ]
    )
    vol = Volume3D(outline_polygon=poly)

    # Translate relative
    rel_trans = RelativeTranslation(meters_east=1000, meters_north=2000)
    vol_rel = vol.translate_relative(rel_trans)

    # Translate absolute
    abs_trans = AbsoluteTranslation(new_latitude=46.0, new_longitude=10.0)
    vol_abs = vol.translate_absolute(abs_trans)

    # Verify that the average vertex is moved correctly
    assert vol_rel.outline_polygon is not None
    avg_rel = vol_rel.outline_polygon.vertex_average()
    expected_rel = poly.vertex_average().offset(1000, 2000)
    assert abs(avg_rel.lat - expected_rel.lat) < 1e-6
    assert abs(avg_rel.lng - expected_rel.lng) < 1e-6

    assert vol_abs.outline_polygon is not None
    avg_abs = vol_abs.outline_polygon.vertex_average()
    assert abs(avg_abs.lat - 46.0) < 1e-6
    assert abs(avg_abs.lng - 10.0) < 1e-6


def test_make_latlng_rect():
    from monitoring.monitorlib.geo import Circle, Volume3D, make_latlng_rect

    circle_vol = Volume3D(outline_circle=Circle.from_meters(34.0, -118.0, 1000.0))
    rect = make_latlng_rect(circle_vol)
    assert rect.contains(s2sphere.LatLng.from_degrees(34.0, -118.0))
