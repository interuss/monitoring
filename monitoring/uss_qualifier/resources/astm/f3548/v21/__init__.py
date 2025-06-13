import warnings

__all__ = ["DSSInstanceResource", "DSSInstancesResource", "PlanningAreaResource"]


def __getattr__(name):
    if name == "PlanningAreaResource":
        warnings.warn(
            "PlanningAreaResource has moved to new_module. Importing it from its current location is deprecated and will be removed in the future.",
            UserWarning,
            stacklevel=2,
        )
        from monitoring.uss_qualifier.resources import PlanningAreaResource

        return PlanningAreaResource
    elif name in {"DSSInstanceResource", "DSSInstancesResource"}:
        from .dss import DSSInstanceResource, DSSInstancesResource

        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
