from abc import ABC, abstractmethod

from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources.resource import Resource


class PluralResource[TSingularResource: Resource](Resource, ABC):
    """Resource that provides multiple instances of a singular resources."""

    def get_associated_participants(self) -> list[ParticipantID]:
        participants = []
        for i in range(self.get_resource_instances_count()):
            resource = self.get_resource_instance(i)
            participants.extend(resource.get_associated_participants())
        return list(dict.fromkeys(participants))

    @abstractmethod
    def get_resource_instances_count(self) -> int:
        """Get the number of singular resources this plural resource contains."""
        raise NotImplementedError()

    @abstractmethod
    def get_resource_instance(self, index: int) -> TSingularResource:
        """Get the specific singular resource at the specified index contained by this plural resource."""
        raise NotImplementedError()
