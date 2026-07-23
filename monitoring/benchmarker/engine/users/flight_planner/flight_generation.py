import uuid
from datetime import datetime, timedelta
from random import Random

from monitoring.benchmarker.configurations.users import (
    FlightExecutionSpecification,
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
    execution: FlightExecutionSpecification | None = None
    random: Random

    def __init__(
        self, spec: FlightGenerationSpecification, user_id: str, random: Random
    ):
        if (
            "independent_time_location_shape" not in spec
            or not spec.independent_time_location_shape
        ):
            raise ValueError(
                "`independent_time_location_shape` not specified for IndependentTimeLocationShape FlightGenerator"
            )

        self.spec = spec.independent_time_location_shape
        if "execution" in spec and spec.execution:
            self.execution = spec.execution

        if "fixed_location" in self.spec.location and self.spec.location.fixed_location:
            pass
        else:
            raise NotImplementedError(
                "No supported location component is specified in independent_time_location_shape.location for user `user_id`"
            )

        if "fixed_volumes" in self.spec.shape and self.spec.shape.fixed_volumes:
            pass
        else:
            raise NotImplementedError(
                "No supported shape component specified in independent_time_location_shape.shape for user `user_id`"
            )

        if self.spec.shape.fixed_volumes and self.spec.location.fixed_location:
            # Check unit/reference match between fixed_location and fixed_volumes
            fixed_vols = self.spec.shape.fixed_volumes
            fixed_loc = self.spec.location.fixed_location
            origin_vert = fixed_vols.origin_vertical
            if (
                fixed_loc.vertical.reference != origin_vert.reference
                or fixed_loc.vertical.units != origin_vert.units
            ):
                raise NotImplementedError(
                    "Combining vertical location and shape with different reference or units is not supported"
                )

        self.random = random

    def generate_flight(self, previous_flight_end: datetime) -> Flight:
        dt = timedelta(seconds=0)
        if "fixed_spacing" in self.spec.time and self.spec.time.fixed_spacing:
            dt += self.spec.time.fixed_spacing.timedelta
        if (
            "uniform_random_spacing" in self.spec.time
            and self.spec.time.uniform_random_spacing
        ):
            dt += self.spec.time.uniform_random_spacing.timedelta * self.random.random()
        t0 = previous_flight_end + dt

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

        time_end = volumes.time_end_not_none.datetime
        actual_end_time = time_end
        if self.execution:
            time_start = volumes.time_start_not_none.datetime
            if (
                "end_flight_after_start" in self.execution
                and self.execution.end_flight_after_start
            ):
                actual_end_time = min(
                    actual_end_time,
                    time_start + self.execution.end_flight_after_start.timedelta,
                )
            if (
                "end_flight_before_end" in self.execution
                and self.execution.end_flight_before_end
            ):
                actual_end_time = min(
                    actual_end_time,
                    time_end - self.execution.end_flight_before_end.timedelta,
                )
            actual_end_time = max(actual_end_time, time_start)

        return Flight(
            id=FlightID(uuid.uuid4()), volumes=volumes, actual_end_time=actual_end_time
        )


def make_flight_generator(
    flight_generation: FlightGenerationSpecification, user_id: str, random: Random
) -> FlightGenerator:
    if (
        "independent_time_location_shape" in flight_generation
        and flight_generation.independent_time_location_shape
    ):
        return IndependentTimeLocationShape(
            flight_generation,
            user_id,
            random,
        )
    else:
        raise ValueError(
            f"No supported flight_generation method specified for user `{user_id}`"
        )
