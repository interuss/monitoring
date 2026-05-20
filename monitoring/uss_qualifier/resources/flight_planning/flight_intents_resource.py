import json
import math

import s2sphere
from implicitdict import ImplicitDict

from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    FlightInfoTemplate,
)
from monitoring.monitorlib.geo import EARTH_CIRCUMFERENCE_M, LatLngBoundingBox
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.transformations import (
    RelativeTranslation,
    Transformation,
)
from monitoring.uss_qualifier.resources.files import load_dict
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntentCollection,
    FlightIntentID,
    FlightIntentsSpecification,
)
from monitoring.uss_qualifier.resources.modifiers import (
    GeospatialModifier,
    GeospatialResource,
)
from monitoring.uss_qualifier.resources.resource import Resource


class FlightIntentsResource(Resource[FlightIntentsSpecification], GeospatialResource):
    _spec: FlightIntentsSpecification
    _intent_collection: FlightIntentCollection

    def __init__(self, specification: FlightIntentsSpecification, resource_origin: str):
        super().__init__(specification, resource_origin)
        self._spec = specification
        has_file = "file" in specification and specification.file
        has_literal = (
            "intent_collection" in specification and specification.intent_collection
        )
        if has_file and has_literal:
            raise ValueError(
                "Only one of `file` or `intent_collection` may be specified in FlightIntentsSpecification"
            )
        if not has_file and not has_literal:
            raise ValueError(
                "One of `file` or `intent_collection` must be specified in FlightIntentsSpecification"
            )
        if has_file:
            self._intent_collection = ImplicitDict.parse(
                load_dict(specification.file), FlightIntentCollection
            )
        elif has_literal:
            self._intent_collection = ImplicitDict.parse(
                json.loads(
                    json.dumps(specification.intent_collection)
                ),  # NB: We need a copy to avoid sharing '_intent_collection' between instances
                FlightIntentCollection,
            )
        if "transformations" in specification and specification.transformations:
            if (
                "transformations" in self._intent_collection
                and self._intent_collection.transformations
            ):
                self._intent_collection.transformations.extend(
                    specification.transformations[::]
                )
            else:
                self._intent_collection.transformations = specification.transformations[  # NB: We do a copy to be independent between instances
                    ::
                ]

    def get_flight_intents(self) -> dict[FlightIntentID, FlightInfoTemplate]:
        return self._intent_collection.resolve()

    def get_extents(self) -> LatLngBoundingBox:
        rect = s2sphere.LatLngRect.empty()
        for template in self.get_flight_intents().values():
            transformations = (
                template.transformations
                if "transformations" in template and template.transformations
                else []
            )
            for vt in template.basic_information.area:
                v4d = Volume4D(volume=vt.resolve_3d())
                for transformation in transformations:
                    v4d = v4d.transform(transformation)
                rect = rect.union(v4d.rect_bounds)
        return LatLngBoundingBox.from_latlng_rect(rect)

    def move(self, meters_east: float, meters_north: float) -> "FlightIntentsResource":
        new_spec = FlightIntentsSpecification(self._spec)

        # Apply the translation as degrees, not meters. RelativeTranslation in
        # meters is converted per-polygon using each polygon's vertex_average as
        # the tangent-plane origin, which yields slightly different absolute
        # offsets for different polygons. That sub-meter drift is enough to break
        # pre-existing intent overlaps (e.g. "tiny_overlap" conflicts). Converting
        # meters → degrees here using the resource's overall extents produces a
        # rigid lat/lng shift applied identically to every vertex.
        extents = self.get_extents()
        lat0 = (extents.lat_min + extents.lat_max) / 2
        longitude_length = EARTH_CIRCUMFERENCE_M * math.cos(math.radians(lat0))

        transformation = Transformation(
            relative_translation=RelativeTranslation(
                degrees_east=meters_east * 360 / longitude_length,
                degrees_north=meters_north * 360 / EARTH_CIRCUMFERENCE_M,
            )
        )

        if "transformations" in new_spec and new_spec.transformations:
            new_spec.transformations = new_spec.transformations + [transformation]
        else:
            new_spec.transformations = [transformation]
        return FlightIntentsResource(new_spec, resource_origin=self.resource_origin)


class FlightIntentsModifier(GeospatialModifier[FlightIntentsResource]):
    pass
