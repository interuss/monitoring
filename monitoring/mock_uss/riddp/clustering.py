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
        return Cluster(
            x_min=self.x_min + (u_min - self.x_min) * random.random(),
            y_min=self.y_min + (v_min - self.y_min) * random.random(),
            x_max=u_max + (self.x_max - u_max) * random.random(),
            y_max=v_max + (self.y_max - v_max) * random.random(),
            points=self.points,
        )

    def extend_size(self, min_area_size: float):
        scale = min_area_size / self.area()

        return Cluster(
            x_min=self.x_min - math.sqrt(scale) * self.width(),
            x_max=self.x_max + math.sqrt(scale) * self.width(),
            y_min=self.y_min - math.sqrt(scale) * self.height(),
            y_max=self.y_max + math.sqrt(scale) * self.height(),
            points=self.points,
        )


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
        cluster = (
            cluster.randomize()
        )  # TODO: Set random seed according to view extents so a static view will have static cluster subdivisions

        min_cluster_area = view_area_sqm * rid_version.min_cluster_size_percent / 100
        if cluster.area() < min_cluster_area:
            # Extend cluster to the minimum area size required by NET0480
            cluster = cluster.extend_size(min_cluster_area)

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
