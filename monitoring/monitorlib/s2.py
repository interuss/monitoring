import math

import s2sphere


def _wrap_dlng_rad(dlng: float) -> float:
    while dlng <= -math.pi:
        dlng += 2 * math.pi
    while dlng > math.pi:
        dlng -= 2 * math.pi
    return dlng


def _parent(cell: s2sphere.CellId, level: int) -> s2sphere.CellId:
    p = cell.parent(level)
    assert p is not None
    return p


def _point_xyz(pt: s2sphere.Point) -> tuple[float, float, float]:
    return (
        pt.dot_prod(s2sphere.Point(1.0, 0.0, 0.0)),
        pt.dot_prod(s2sphere.Point(0.0, 1.0, 0.0)),
        pt.dot_prod(s2sphere.Point(0.0, 0.0, 1.0)),
    )


def cell_of(lat_degrees: float, lng_degrees: float, level: int) -> s2sphere.CellId:
    """Return S2 cell at specified level that contains the specified point."""
    return _parent(
        s2sphere.CellId.from_lat_lng(
            s2sphere.LatLng.from_degrees(lat_degrees, lng_degrees)
        ),
        level,
    )


def offset_cell(cell: s2sphere.CellId, east: int, north: int) -> s2sphere.CellId:
    """Return S2 cell at the same level that is `east` cells to the east and `north` cells to the north.

    For instance, east=1,north=0 retrieves the neighboring S2 cell to the east.
    Negative `east` or `north` retrieves the cell to the west or south, respectively."""
    if east == 0 and north == 0:
        return cell

    level = cell.level()
    size = cell.get_size_ij(level)
    face, i, j, _ = cell.to_face_ij_orientation()

    # The 4 edge neighbors returned by get_edge_neighbors() correspond to
    # (0, -size), (size, 0), (0, size), (-size, 0) in (i, j) coordinates,
    # which are in counterclockwise order on the sphere.
    dirs = [(0, -size), (size, 0), (0, size), (-size, 0)]

    center = cell.to_lat_lng()
    lat0 = center.lat().radians
    lng0 = center.lng().radians
    neighbors = cell.get_edge_neighbors()
    vecs = []
    for n in neighbors:
        assert n is not None
        ll = n.to_lat_lng()
        dlat = ll.lat().radians - lat0
        dlng = _wrap_dlng_rad(ll.lng().radians - lng0) * math.cos(lat0)
        vecs.append((dlng, dlat))

    # Find cyclic shift k that maximizes alignment with (East, North, West, South)
    best_k = max(
        range(4),
        key=lambda k: (
            vecs[k][0]
            + vecs[(k + 1) % 4][1]
            - vecs[(k + 2) % 4][0]
            - vecs[(k + 3) % 4][1]
        ),
    )

    v_east = dirs[best_k]
    v_north = dirs[(best_k + 1) % 4]

    target_i = i + east * v_east[0] + north * v_north[0]
    target_j = j + east * v_east[1] + north * v_north[1]

    if (
        0 <= target_i < s2sphere.CellId.MAX_SIZE
        and 0 <= target_j < s2sphere.CellId.MAX_SIZE
    ):
        return _parent(s2sphere.CellId.from_face_ij(face, target_i, target_j), level)
    else:
        scale = 1.0 / s2sphere.CellId.MAX_SIZE
        u = scale * ((target_i << 1) + 1 - s2sphere.CellId.MAX_SIZE)
        v = scale * ((target_j << 1) + 1 - s2sphere.CellId.MAX_SIZE)
        new_face, u, v = s2sphere.xyz_to_face_uv(s2sphere.face_uv_to_xyz(face, u, v))
        return _parent(
            s2sphere.CellId.from_face_ij(
                new_face,
                s2sphere.CellId.st_to_ij(0.5 * (u + 1)),
                s2sphere.CellId.st_to_ij(0.5 * (v + 1)),
            ),
            level,
        )


def inscribed_latlng_rect(cell: s2sphere.CellId) -> s2sphere.LatLngRect:
    """Return a large inscribed lat-lng rectangle fully contained within the specified S2 cell.

    No points in the lat-lng rectangle may lie within any other S2 cell at the specified level
    (i.e., they may not be on the edge between two S2 cells)."""
    if cell.level() == 0:
        if cell.face() == 2:
            return s2sphere.LatLngRect(
                s2sphere.LatLng.from_radians(math.pi / 4 + 1e-6, -math.pi),
                s2sphere.LatLng.from_radians(math.pi / 2 - 1e-6, math.pi),
            )
        if cell.face() == 5:
            return s2sphere.LatLngRect(
                s2sphere.LatLng.from_radians(-math.pi / 2 + 1e-6, -math.pi),
                s2sphere.LatLng.from_radians(-math.pi / 4 - 1e-6, math.pi),
            )

    s2_cell = s2sphere.Cell(cell)
    lng0 = cell.to_lat_lng().lng().radians
    v_lngs = []
    for k in range(4):
        pt = s2_cell.get_vertex(k)
        _, _, pz = _point_xyz(pt)
        if abs(pz) < 1.0 - 1e-12:
            v = s2sphere.LatLng.from_point(pt)
            v_lngs.append(lng0 + _wrap_dlng_rad(v.lng().radians - lng0))
    v_lngs.sort()
    lng_min, lng_max = v_lngs[0], v_lngs[-1]
    span = lng_max - lng_min

    edges = []
    for k in range(4):
        e = s2_cell.get_edge(k)
        nx, ny, nz = _point_xyz(e)
        stat = math.atan2(ny, nx)
        stat = lng0 + _wrap_dlng_rad(stat - lng0)
        edges.append((nx, ny, nz, stat))

    def valid_lat_interval(lng_lo: float, lng_hi: float) -> tuple[float, float]:
        lat_lo_bound = -math.pi / 2
        lat_hi_bound = math.pi / 2
        for nx, ny, nz, stat in edges:
            if abs(nz) < 1e-15:
                if (
                    nx * math.cos(lng_lo) + ny * math.sin(lng_lo) <= 0
                    or nx * math.cos(lng_hi) + ny * math.sin(lng_hi) <= 0
                ):
                    return 1.0, -1.0
                continue
            v0 = math.atan(-(nx * math.cos(lng_lo) + ny * math.sin(lng_lo)) / nz)
            v1 = math.atan(-(nx * math.cos(lng_hi) + ny * math.sin(lng_hi)) / nz)
            if nz > 0:
                m = v0 if v0 > v1 else v1
                if lng_lo < stat < lng_hi:
                    vs = math.atan(-(nx * math.cos(stat) + ny * math.sin(stat)) / nz)
                    if vs > m:
                        m = vs
                if m > lat_lo_bound:
                    lat_lo_bound = m
            else:
                m = v0 if v0 < v1 else v1
                if lng_lo < stat < lng_hi:
                    vs = math.atan(-(nx * math.cos(stat) + ny * math.sin(stat)) / nz)
                    if vs < m:
                        m = vs
                if m < lat_hi_bound:
                    lat_hi_bound = m
        return lat_lo_bound, lat_hi_bound

    best_area = -1.0
    best_lng_lo = lng_min
    best_lng_hi = lng_max

    grid_pts = sorted(set([lng_min + span * i / 20.0 for i in range(21)] + v_lngs))
    for i in range(len(grid_pts)):
        lo = grid_pts[i]
        for j in range(i + 1, len(grid_pts)):
            hi = grid_pts[j]
            lat_lo, lat_hi = valid_lat_interval(lo, hi)
            if lat_hi > lat_lo:
                area = (hi - lo) * (math.sin(lat_hi) - math.sin(lat_lo))
                if area > best_area:
                    best_area = area
                    best_lng_lo, best_lng_hi = lo, hi

    step = span / 20.0
    for _ in range(25):
        improved = False
        for d_lo in (-step, 0.0, step):
            lo = best_lng_lo + d_lo
            if lo < lng_min:
                lo = lng_min
            for d_hi in (-step, 0.0, step):
                if d_lo == 0.0 and d_hi == 0.0:
                    continue
                hi = best_lng_hi + d_hi
                if hi > lng_max:
                    hi = lng_max
                if hi <= lo:
                    continue
                lat_lo, lat_hi = valid_lat_interval(lo, hi)
                if lat_hi > lat_lo:
                    area = (hi - lo) * (math.sin(lat_hi) - math.sin(lat_lo))
                    if area > best_area:
                        best_area = area
                        best_lng_lo, best_lng_hi = lo, hi
                        improved = True
        if not improved:
            step *= 0.5

    lat_lo, lat_hi = valid_lat_interval(best_lng_lo, best_lng_hi)
    d_lat = (lat_hi - lat_lo) * 1e-6
    d_lng = (best_lng_hi - best_lng_lo) * 1e-6
    lat_lo += d_lat
    lat_hi -= d_lat
    best_lng_lo += d_lng
    best_lng_hi -= d_lng
    return s2sphere.LatLngRect(
        s2sphere.LatLng.from_radians(lat_lo, _wrap_dlng_rad(best_lng_lo)),
        s2sphere.LatLng.from_radians(lat_hi, _wrap_dlng_rad(best_lng_hi)),
    )


def rect_str(r: s2sphere.LatLngRect) -> str:
    return f"(lat {r.lat_lo().degrees}, lng {r.lng_lo().degrees})-(lat {r.lat_hi().degrees}, lng {r.lng_hi().degrees})"
