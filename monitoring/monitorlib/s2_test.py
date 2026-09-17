import math

import s2sphere

from monitoring.monitorlib.s2 import (
    _parent,
    _point_xyz,
    _wrap_dlng_rad,
    cell_of,
    inscribed_latlng_rect,
    offset_cell,
)


def test_cell_of():
    for level in [0, 5, 13, 20, 30]:
        for lat, lng in [(37.4, -122.1), (47.3, 8.5), (-33.8, 151.2), (0.0, 0.0)]:
            cell = cell_of(lat, lng, level)
            assert cell.level() == level
            pt = s2sphere.LatLng.from_degrees(lat, lng).to_point()
            assert s2sphere.Cell(cell).contains(pt)


def test_offset_cell_neighbors():
    for level in [4, 10, 13]:
        for lat in range(-70, 71, 20):
            for lng in range(-180, 180, 45):
                cell = cell_of(lat, lng, level)
                assert offset_cell(cell, 0, 0) == cell

                n_east = offset_cell(cell, 1, 0)
                n_west = offset_cell(cell, -1, 0)
                n_north = offset_cell(cell, 0, 1)
                n_south = offset_cell(cell, 0, -1)

                assert {n_east, n_west, n_north, n_south} == set(
                    cell.get_edge_neighbors()
                )
                assert (
                    n_north.to_lat_lng().lat().radians
                    > n_south.to_lat_lng().lat().radians
                )
                assert (
                    _wrap_dlng_rad(
                        n_east.to_lat_lng().lng().radians
                        - n_west.to_lat_lng().lng().radians
                    )
                    > 0
                )


def test_offset_cell_multi_step_and_boundaries():
    # Test multi-step offsets on same face
    cell = cell_of(37.4, -122.1, 13)
    c_offset = offset_cell(cell, 4, -3)
    assert c_offset.level() == 13
    assert offset_cell(c_offset, -4, 3) == cell

    # Test face boundary crossings at all 6 faces
    level = 10
    c_dummy = s2sphere.CellId.from_face_pos_level(0, 0, level)
    assert c_dummy is not None
    size = c_dummy.get_size_ij(level)
    max_ij = s2sphere.CellId.MAX_SIZE - size
    for face in range(6):
        for i in [0, max_ij]:
            for j in [0, max_ij]:
                c = _parent(s2sphere.CellId.from_face_ij(face, i, j), level)
                assert {
                    offset_cell(c, 1, 0),
                    offset_cell(c, -1, 0),
                    offset_cell(c, 0, 1),
                    offset_cell(c, 0, -1),
                } == set(c.get_edge_neighbors())


def _verify_rect_strictly_in_cell(cell: s2sphere.CellId, rect: s2sphere.LatLngRect):
    assert rect.is_valid() and not rect.is_empty()
    s2_cell = s2sphere.Cell(cell)
    level = cell.level()
    lat_lo, lat_hi = rect.lat_lo().radians, rect.lat_hi().radians
    lng_lo, lng_hi = rect.lng_lo().radians, rect.lng_hi().radians
    is_full_lng = rect.lng().is_full()
    dlng = 2 * math.pi if is_full_lng else _wrap_dlng_rad(lng_hi - lng_lo)

    for u in [0.0, 0.25, 0.5, 0.75, 1.0]:
        for v in [0.0, 0.25, 0.5, 0.75, 1.0]:
            lat = lat_lo + u * (lat_hi - lat_lo)
            lng = _wrap_dlng_rad(lng_lo + v * dlng)
            ll = s2sphere.LatLng.from_radians(lat, lng)
            assert s2sphere.CellId.from_lat_lng(ll).parent(level) == cell
            pt = ll.to_point()
            assert s2_cell.contains(pt)
            px, py, pz = _point_xyz(pt)
            for k in range(4):
                edge = s2_cell.get_edge(k)
                ex, ey, ez = _point_xyz(edge)
                dot = px * ex + py * ey + pz * ez
                assert dot > 0


def test_inscribed_latlng_rect():
    # Test level-0 and level-1 cells across all 6 faces
    for face in range(6):
        c0 = s2sphere.CellId.from_face_pos_level(face, 0, 0)
        assert c0 is not None
        _verify_rect_strictly_in_cell(c0, inscribed_latlng_rect(c0))
        for c1 in c0.children():
            assert c1 is not None
            _verify_rect_strictly_in_cell(c1, inscribed_latlng_rect(c1))

    # Test various levels and locations across the globe, verifying large area
    for level in [4, 9, 13, 18]:
        for lat, lng, min_area_ratio in [
            (0.0, 0.0, 0.99),  # Equator: cell is nearly rectangular
            (37.4, -122.1, 0.60),  # Mid-latitude parallelogram
            (47.3, 8.5, 0.65),  # Polar face cell
            (60.0, 45.0, 0.48),  # 45-degree rotated diamond cell on polar face
            (-33.8, 151.2, 0.60),  # Southern hemisphere
        ]:
            cell = cell_of(lat, lng, level)
            rect = inscribed_latlng_rect(cell)
            _verify_rect_strictly_in_cell(cell, rect)
            area_ratio = rect.area() / s2sphere.Cell(cell).exact_area()
            assert area_ratio >= min_area_ratio, (
                f"Expected area ratio >= {min_area_ratio} at ({lat}, {lng}) level {level}, got {area_ratio}"
            )
