from __future__ import annotations

from urllib.parse import urlparse

from implicitdict import ImplicitDict, Optional

from monitoring.monitorlib import infrastructure
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.reports.report import ParticipantID
from monitoring.uss_qualifier.resources.astm.dss import NotificationIndexImplementation
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource
from monitoring.uss_qualifier.resources.resource import Resource


class DSSInstanceSpecification(ImplicitDict):
    participant_id: ParticipantID
    """ID of the USS responsible for this DSS instance"""

    rid_version: RIDVersion
    """Version of ASTM F3411 implemented by this DSS instance"""

    base_url: str
    """Base URL for the DSS instance according to the ASTM F3411 API appropriate to the specified rid_version"""

    notification_index_implementation: Optional[NotificationIndexImplementation]
    """Style of implementation this instance uses for notification index.
    
    If not specified, TimeBased is assumed."""

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        try:
            urlparse(self.base_url)
        except ValueError:
            raise ValueError("DSSInstanceConfiguration.base_url must be a URL")


class DSSInstance:
    participant_id: ParticipantID
    rid_version: RIDVersion
    base_url: str
    client: infrastructure.UTMClientSession
    notification_index_implementation: NotificationIndexImplementation

    def __init__(
        self,
        participant_id: ParticipantID,
        base_url: str,
        rid_version: RIDVersion,
        client: UTMClientSession,
        notification_index_implementation: NotificationIndexImplementation,
    ):
        self.participant_id = participant_id
        self.base_url = base_url
        self.rid_version = rid_version
        self.client = client
        self.notification_index_implementation = notification_index_implementation

    def is_same_as(self, other: DSSInstance) -> bool:
        return (
            self.participant_id == other.participant_id
            and self.rid_version == other.rid_version
            and self.base_url == other.base_url
            and self.notification_index_implementation
            == other.notification_index_implementation
        )


class DSSInstanceResource(Resource[DSSInstanceSpecification]):
    dss_instance: DSSInstance

    def __init__(
        self,
        specification: DSSInstanceSpecification,
        resource_origin: str,
        auth_adapter: AuthAdapterResource,
    ):
        super().__init__(specification, resource_origin)

        # Note that the current implementation does not support acting as just a
        # SP accessing the DSS or just a DP accessing the DSS, but this could be
        # improved.
        auth_adapter.assert_scopes_available(
            scopes_required={
                specification.rid_version.scope_sp(): "act as an ASTM F3411 NetRID Service Provider to facilitate testing",
                specification.rid_version.scope_dp(): "act as an ASTM F3411 NetRID Display Provider to facilitate testing",
            },
            consumer_name=f"{self.__class__.__name__} resource",
        )

        self.dss_instance = DSSInstance(
            specification.participant_id,
            specification.base_url,
            specification.rid_version,
            infrastructure.utm_client_session_factory.get_session(
                specification.base_url, auth_adapter.adapter
            ),
            specification.notification_index_implementation
            if "notification_index_implementation" in specification
            and specification.notification_index_implementation
            else NotificationIndexImplementation.TimedBased,
        )

    @classmethod
    def from_dss_instance(
        cls, dss_instance: DSSInstance, resource_origin: str
    ) -> DSSInstanceResource:
        self = cls.__new__(cls)
        self.dss_instance = dss_instance
        self.resource_origin = resource_origin
        return self


class DSSInstancesSpecification(ImplicitDict):
    dss_instances: list[DSSInstanceSpecification]


class DSSInstancesResource(Resource[DSSInstancesSpecification]):
    dss_instances: list[DSSInstance]

    def __init__(
        self,
        specification: DSSInstancesSpecification,
        resource_origin: str,
        auth_adapter: AuthAdapterResource,
    ):
        super().__init__(specification, resource_origin)
        self.dss_instances = [
            DSSInstanceResource(
                s, f"instance {i + 1} in {resource_origin}", auth_adapter
            ).dss_instance
            for i, s in enumerate(specification.dss_instances)
        ]
