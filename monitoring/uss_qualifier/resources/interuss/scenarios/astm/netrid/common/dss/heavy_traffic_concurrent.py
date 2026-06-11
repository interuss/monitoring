from implicitdict import ImplicitDict

from monitoring.uss_qualifier.resources.resource import ValueResource


class HeavyTrafficConcurrentBehaviorSpecification(ImplicitDict):
    concurrency: int = 20
    """Maximum number of simultaneous requests"""

    isa_count: int = 100
    """Number of ISAs to manage"""


class HeavyTrafficConcurrentBehaviorResource(
    ValueResource[HeavyTrafficConcurrentBehaviorSpecification]
):
    pass
