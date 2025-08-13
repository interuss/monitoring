import warnings

__all__ = ["DSSInstanceResource", "DSSInstancesResource", "PlanningAreaResource"]


# TODO remove the exposure of PlanningAreaResource (and revert this __init__.py file to a normal state) when enough time has passed
def __getattr__(name):
    if name == "PlanningAreaResource":
        warnings.warn(
            "PlanningAreaResource has moved from 'resources.astm.f3548.v21' to 'resources'. Importing it from its current location is deprecated and will be removed in the future.",
            UserWarning,
            stacklevel=2,
        )
        from monitoring.uss_qualifier.resources import PlanningAreaResource

        return PlanningAreaResource
    elif name in {"DSSInstanceResource", "DSSInstancesResource"}:
        from .dss import DSSInstanceResource, DSSInstancesResource  # noqa F401

        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
