import math
import random

import s2sphere
from implicitdict import ImplicitDict
from s2sphere import LatLngRect
from uas_standards.interuss.automated_testing.rid.v1 import (
    observation as observation_api,
)

from monitoring.monitorlib import geo
from monitoring.monitorlib.rid import RIDVersion


class Point:
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
    points: list[Point]

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

        # We create a base shift so the current x_min/y_min are on the minimum
        # value possible
        x_offset = u_min - self.x_min
        y_offset = v_min - self.y_min

        # We move back the shift value to at most (shifted x_max - u_max), to keep the
        # windows with all points.
        # If the size is too small, this will fail, but the cluster is already
        # bad
        x_offset -= random.uniform(0, self.x_max + x_offset - u_max)
        y_offset -= random.uniform(0, self.y_max + y_offset - v_max)

        # Proof it work:
        #
        # If random choose the minimum value:
        # x_offset = u_min - self.x_min - 0
        # x_min = self.x_min + x_offset
        #       = self.x_min + u_min - self.x_min
        #       = u_min
        # So if the cluster is big enough, our min will be on the minimum edge of our
        # points
        #
        # If random choose the maximum value:
        # x_offset = u_min - self.x_min - (self.x_max + x_offset - u_max)
        # x_offset = u_min - self.x_min - self.x_max - x_offset + u_max
        # x_max = self.x_max + x_offset
        # x_max = self.x_max + u_min - self.x_min - self.x_max - u_min + self.x_min + u_max
        #       = u_max
        # So if the cluster is big enough, our max will be on the maximum edge of our
        # points

        return Cluster(
            x_min=self.x_min + x_offset,
            y_min=self.y_min + y_offset,
            x_max=self.x_max + x_offset,
            y_max=self.y_max + y_offset,
            points=list(self.points),
        )

    def extend(self, rid_version: RIDVersion, view_area_sqm: float):
        """Extend cluster size and dimensions to the minimum required"""

        cluster = self

        # Extend cluster width to match the minimum distance required by NET0490
        if cluster.width() < 2 * rid_version.min_obfuscation_distance_m:
            delta = rid_version.min_obfuscation_distance_m - cluster.width() / 2
            cluster = Cluster(
                x_min=cluster.x_min - delta,
                x_max=cluster.x_max + delta,
                y_min=cluster.y_min,
                y_max=cluster.y_max,
                points=list(cluster.points),
            )

        # Extend cluster height to match the minimum distance required by NET0490
        if cluster.height() < 2 * rid_version.min_obfuscation_distance_m:
            delta = rid_version.min_obfuscation_distance_m - cluster.height() / 2
            cluster = Cluster(
                x_min=cluster.x_min,
                x_max=cluster.x_max,
                y_min=cluster.y_min - delta,
                y_max=cluster.y_max + delta,
                points=list(cluster.points),
            )

        # Extend cluster to the minimum area size required by NET0480
        min_cluster_area = view_area_sqm * rid_version.min_cluster_size_percent / 100
        if cluster.area() < min_cluster_area:
            scale = math.sqrt(min_cluster_area / cluster.area()) / 2
            cluster = Cluster(
                x_min=cluster.x_min - scale * cluster.width(),
                x_max=cluster.x_max + scale * cluster.width(),
                y_min=cluster.y_min - scale * cluster.height(),
                y_max=cluster.y_max + scale * cluster.height(),
                points=list(cluster.points),
            )

        return cluster


def make_clusters(
    flights: list[observation_api.Flight],
    view_min: s2sphere.LatLng,
    view_max: s2sphere.LatLng,
    rid_version: RIDVersion,
) -> list[observation_api.Cluster]:
    if not flights:
        return []

    # Make the initial cluster
    points: list[Point] = [
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
    clusters: list[Cluster] = [
        Cluster(x_min=0, y_min=0, x_max=x_max, y_max=y_max, points=points)
    ]

    # TODO: subdivide cluster into many clusters

    view_area_sqm = geo.area_of_latlngrect(LatLngRect(view_min, view_max))

    result: list[observation_api.Cluster] = []
    for cluster in clusters:
        cluster = cluster.extend(rid_version, view_area_sqm)

        # Offset cluster
        cluster = cluster.randomize()  # TODO: Set random seed according to view extents so a static view will have static cluster subdivisions

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
