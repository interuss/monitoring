from implicitdict import ImplicitDict


class RelativeTranslation(ImplicitDict):
    """Offset a geo feature by a particular amount."""

    meters_east: float | None
    """Number of meters east to translate."""

    meters_north: float | None
    """Number of meters north to translate."""

    meters_up: float | None
    """Number of meters upward to translate."""

    degrees_east: float | None
    """Number of degrees of longitude east to translate."""

    degrees_north: float | None
    """Number of degrees of latitude north to translate."""


class AbsoluteTranslation(ImplicitDict):
    """Move a geo feature to a specified location."""

    new_latitude: float
    """The new latitude at which the feature should be located (degrees)."""

    new_longitude: float
    """The new longitude at which the feature should be located (degrees)."""


class Transformation(ImplicitDict):
    """A transformation to apply to a geotemporal feature.  Exactly one field must be specified."""

    relative_translation: RelativeTranslation | None

    absolute_translation: AbsoluteTranslation | None
