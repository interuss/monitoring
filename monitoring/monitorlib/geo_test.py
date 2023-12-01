from typing import List, Tuple

from s2sphere import LatLng

from monitoring.monitorlib.geo import generate_slight_overlap_area


def _points(in_points: List[Tuple[float, float]]) -> List[LatLng]:
    return [LatLng.from_degrees(*p) for p in in_points]


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
