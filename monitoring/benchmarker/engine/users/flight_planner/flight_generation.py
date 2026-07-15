import uuid
from datetime import datetime

from monitoring.benchmarker.configurations.users import (
    FlightGenerationSpecification,
    IndependentComponentsFlightGenerationSpecification,
)
from monitoring.benchmarker.engine.users.flight_planner.framework import (
    Flight,
    FlightGenerator,
    FlightID,
)
from monitoring.monitorlib.geo import (
    AltitudeDatum,
    DistanceUnits,
    RelativeTranslation,
    Transformation,
)
from monitoring.monitorlib.geotemporal import Volume4DCollection


class IndependentTimeLocationShape(FlightGenerator):
    spec: IndependentComponentsFlightGenerationSpecification

    def __init__(
        self, spec: IndependentComponentsFlightGenerationSpecification, user_id: str
    ):
        self.spec = spec

        if "fixed_spacing" in spec.time and spec.time.fixed_spacing:
            pass
        else:
            raise NotImplementedError(
                f"No supported time component is specified in independent_time_location_shape.time for user `{user_id}`"
            )

        if "fixed_location" in spec.location and spec.location.fixed_location:
            pass
        else:
            raise NotImplementedError(
                "No supported location component is specified in independent_time_location_shape.location for user `user_id`"
            )

        if "fixed_volumes" in spec.shape and spec.shape.fixed_volumes:
            pass
        else:
            raise NotImplementedError(
                "No supported shape component specified in independent_time_location_shape.shape for user `user_id`"
            )

        if spec.shape.fixed_volumes and spec.location.fixed_location:
            # Check unit/reference match between fixed_location and fixed_volumes
            fixed_vols = spec.shape.fixed_volumes
            fixed_loc = spec.location.fixed_location
            origin_vert = fixed_vols.origin_vertical
            if (
                fixed_loc.vertical.reference != origin_vert.reference
                or fixed_loc.vertical.units != origin_vert.units
            ):
                raise NotImplementedError(
                    "Combining vertical location and shape with different reference or units is not supported"
                )

    def generate_flight(self, previous_flight_end: datetime) -> Flight:
        if self.spec.time.fixed_spacing:
            t0 = previous_flight_end + self.spec.time.fixed_spacing.timedelta
        else:
            raise NotImplementedError("Specified time component not implemented")

        if self.spec.location.fixed_location:
            xy = self.spec.location.fixed_location.horizontal
            z = self.spec.location.fixed_location.vertical
            if z.units != DistanceUnits.M:
                raise NotImplementedError(
                    "Only meters are supported for fixed_location altitude"
                )
            if z.reference != AltitudeDatum.W84:
                raise NotImplementedError(
                    "Only W84 is supported for fixed_location altitude"
                )
        else:
            raise NotImplementedError("Specified location component not implemented")

        if self.spec.shape.fixed_volumes:
            origin_h = self.spec.shape.fixed_volumes.origin_horizontal
            origin_v = self.spec.shape.fixed_volumes.origin_vertical
            if origin_v.units != DistanceUnits.M:
                raise NotImplementedError(
                    "Only meters are supported for fixed_volumes vertical origin"
                )
            if origin_v.reference != AltitudeDatum.W84:
                raise NotImplementedError(
                    "Only W84 is supported for fixed_volumes vertical origin"
                )
            transformation = Transformation(
                relative_translation=RelativeTranslation(
                    degrees_east=xy.lng - origin_h.lng,
                    degrees_north=xy.lat - origin_h.lat,
                    meters_up=z.value - origin_v.value,
                    reference_center=origin_h,
                )
            )
            dt = t0 - self.spec.shape.fixed_volumes.origin_time.datetime
            volumes = Volume4DCollection()
            for fixed_volume in self.spec.shape.fixed_volumes.volumes:
                volumes.append(fixed_volume.offset_time(dt).transform(transformation))
        else:
            raise NotImplementedError("Specified shape component not implemented")

        return Flight(id=FlightID(uuid.uuid4()), volumes=volumes)


def make_flight_generator(
    flight_generation: FlightGenerationSpecification, user_id: str
) -> FlightGenerator:
    if (
        "independent_time_location_shape" in flight_generation
        and flight_generation.independent_time_location_shape
    ):
        return IndependentTimeLocationShape(
            flight_generation.independent_time_location_shape,
            user_id,
        )
    else:
        raise ValueError(
            f"No supported flight_generation method specified for user `{user_id}`"
        )
