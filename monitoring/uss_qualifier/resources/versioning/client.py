from typing import Optional, List

from implicitdict import ImplicitDict

from monitoring.monitorlib.clients.versioning.client import VersioningClient
from monitoring.monitorlib.clients.versioning.client_interuss import (
    InterUSSVersioningClient,
)
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.uss_qualifier.reports.report import ParticipantID
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource
from monitoring.uss_qualifier.resources.resource import Resource


class InterUSSVersionProvider(ImplicitDict):
    base_url: str
    """The base URL at which the participant is hosting its implementation of the InterUSS automated testing versioning API."""


class VersionProviderSpecification(ImplicitDict):
    interuss: Optional[InterUSSVersionProvider] = None
    """Populated when the version provider is using the InterUSS automated testing versioning API to provide versioning information."""

    participant_id: ParticipantID
    """Test participant providing system versions."""


class VersionProvidersSpecification(ImplicitDict):
    instances: List[VersionProviderSpecification]


class VersionProvidersResource(Resource[VersionProvidersSpecification]):
    version_providers: List[VersioningClient]

    def __init__(
        self,
        specification: VersionProvidersSpecification,
        auth_adapter: AuthAdapterResource,
    ):
        self.version_providers = []
        for instance in specification.instances:
            if "interuss" in instance and instance.interuss:
                session = UTMClientSession(
                    prefix_url=instance.interuss.base_url,
                    auth_adapter=auth_adapter.adapter,
                )
                self.version_providers.append(
                    InterUSSVersioningClient(
                        session=session, participant_id=instance.participant_id
                    )
                )
            else:
                raise ValueError(
                    f"VersioningProviderSpecification for {instance.participant_id} did not specify a valid means to obtain versioning information"
                )
