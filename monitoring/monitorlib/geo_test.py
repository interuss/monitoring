from typing import List, Tuple

from s2sphere import LatLng

from monitoring.monitorlib.geo import (
    generate_area_in_vicinity,
    generate_slight_overlap_area,
)

MAX_DIFFERENCE = 0.001


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


def _approx_equals(p1: List[LatLng], p2: List[LatLng]) -> bool:
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
