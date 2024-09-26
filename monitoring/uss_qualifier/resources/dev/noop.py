from implicitdict import ImplicitDict

from monitoring.uss_qualifier.resources.resource import Resource


class NoOpSpecification(ImplicitDict):
    sleep_secs: int
    """Duration for which to sleep, expressed in seconds."""


class NoOpResource(Resource[NoOpSpecification]):
    sleep_secs: int

    def __init__(self, specification: NoOpSpecification, resource_origin: str):
        super(NoOpResource, self).__init__(specification, resource_origin)
        self.sleep_secs = specification.sleep_secs
