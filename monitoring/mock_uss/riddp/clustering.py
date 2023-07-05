import math
import random
from typing import List
from loguru import logger

import s2sphere
from s2sphere import LatLngRect

from monitoring.monitorlib import geo
from implicitdict import ImplicitDict

from monitoring.monitorlib.rid import RIDVersion
from monitoring.monitorlib.rid_automated_testing import observation_api


class Point(object):
    x: float
    y: float

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y


class Cluster(ImplicitDict):
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    points: List[Point]

    def width(self):
        return math.fabs(self.x_max - self.x_min)

    def height(self):
        return math.fabs(self.y_max - self.y_min)

    def area(self):
        return self.width() * self.height()

    def randomize(self):
        u_min = min(p.x for p in self.points)
        v_min = min(p.y for p in self.points)
        u_max = max(p.x for p in self.points)
        v_max = max(p.y for p in self.points)

        x_offset = random.uniform(-u_max, u_min)
        y_offset = random.uniform(-v_max, v_min)
        return Cluster(
            x_min=self.x_min + x_offset,
            y_min=self.y_min + y_offset,
            x_max=self.x_max + x_offset,
            y_max=self.y_max + y_offset,
            points=self.points,
        )

    def extend_size(self, min_area_size: float):
        if self.area() < min_area_size:
            scale = math.sqrt(min_area_size / self.area()) / 2
            return Cluster(
                x_min=self.x_min - scale * self.width(),
                x_max=self.x_max + scale * self.width(),
                y_min=self.y_min - scale * self.height(),
                y_max=self.y_max + scale * self.height(),
                points=self.points,
            )
        else:
            return self

    def extend_dimensions(self, min_dimensions: float):
        cluster = self
        if cluster.width() < min_dimensions:
            delta = min_dimensions - cluster.width()
            cluster = Cluster(
                x_min=cluster.x_min - delta / 2,
                x_max=cluster.x_max + delta / 2,
                y_min=cluster.y_min,
                y_max=cluster.y_max,
                points=cluster.points,
            )

        if cluster.height() < min_dimensions:
            delta = min_dimensions - cluster.height()
            cluster = Cluster(
                x_min=cluster.x_min,
                x_max=cluster.x_max,
                y_min=cluster.y_min - delta / 2,
                y_max=cluster.y_max + delta / 2,
                points=cluster.points,
            )
        return cluster


def make_clusters(
    flights: List[observation_api.Flight],
    view_min: s2sphere.LatLng,
    view_max: s2sphere.LatLng,
    rid_version: RIDVersion,
) -> List[observation_api.Cluster]:
    if not flights:
        return []

    # Make the initial cluster
    points: List[Point] = [
        Point(
            *geo.flatten(
                view_min,
                s2sphere.LatLng.from_degrees(
                    flight.most_recent_position.lat, flight.most_recent_position.lng
                ),
            )
        )
        for flight in flights
    ]
    x_max, y_max = geo.flatten(view_min, view_max)
    clusters: List[Cluster] = [
        Cluster(x_min=0, y_min=0, x_max=x_max, y_max=y_max, points=points)
    ]

    # TODO: subdivide cluster into many clusters

    view_area_sqm = geo.area_of_latlngrect(LatLngRect(view_min, view_max))

    result: List[observation_api.Cluster] = []
    for cluster in clusters:
        # Extend cluster height and width to the minimum dimensions required by NET0490
        cluster = cluster.extend_dimensions(2 * rid_version.min_obfuscation_distance_m)

        # Extend cluster to the minimum area size required by NET0480
        min_cluster_area = view_area_sqm * rid_version.min_cluster_size_percent / 100
        cluster = cluster.extend_size(min_cluster_area)

        # Offset cluster
        cluster = (
            cluster.randomize()
        )  # TODO: Set random seed according to view extents so a static view will have static cluster subdivisions

        corners = LatLngRect(
            geo.unflatten(view_min, (cluster.x_min, cluster.y_min)),
            geo.unflatten(view_min, (cluster.x_max, cluster.y_max)),
        )
        result.append(
            observation_api.Cluster(
                corners=[
                    observation_api.Position(
                        lat=corners.lat_lo().degrees,
                        lng=corners.lng_lo().degrees,
                    ),
                    observation_api.Position(
                        lat=corners.lat_hi().degrees,
                        lng=corners.lng_hi().degrees,
                    ),
                ],
                area_sqm=geo.area_of_latlngrect(corners),
                number_of_flights=len(cluster.points),
            )
        )

    return result
