from abc import ABC, abstractmethod

from monitoring.uss_qualifier.resources.resource import Resource


class PluralResource[TSingularResource: Resource](Resource, ABC):
    """Resource that provides multiple instances of a singular resources."""

    @abstractmethod
    def get_resource_instances_count(self) -> int:
        """Get the number of singular resources this plural resource contains."""
        raise NotImplementedError()

    @abstractmethod
    def get_resource_instance(self, index: int) -> TSingularResource:
        """Get the specific singular resource at the specified index contained by this plural resource."""
        raise NotImplementedError()
