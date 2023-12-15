from typing import Optional

from implicitdict import ImplicitDict


class RelativeTranslation(ImplicitDict):
    """Offset a geo feature by a particular amount."""

    meters_east: Optional[float]
    """Number of meters east to translate."""

    meters_north: Optional[float]
    """Number of meters north to translate."""

    meters_up: Optional[float]
    """Number of meters upward to translate."""

    degrees_east: Optional[float]
    """Number of degrees of longitude east to translate."""

    degrees_north: Optional[float]
    """Number of degrees of latitude north to translate."""


class AbsoluteTranslation(ImplicitDict):
    """Move a geo feature to a specified location."""

    new_latitude: float
    """The new latitude at which the feature should be located (degrees)."""

    new_longitude: float
    """The new longitude at which the feature should be located (degrees)."""


class Transformation(ImplicitDict):
    """A transformation to apply to a geotemporal feature.  Exactly one field must be specified."""

    relative_translation: Optional[RelativeTranslation]

    absolute_translation: Optional[AbsoluteTranslation]
