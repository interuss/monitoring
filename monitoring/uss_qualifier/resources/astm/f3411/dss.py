from __future__ import annotations
from typing import List, Optional
from urllib.parse import urlparse

from implicitdict import ImplicitDict

from monitoring.monitorlib import infrastructure
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.reports.report import ParticipantID
from monitoring.uss_qualifier.resources.resource import Resource
from monitoring.uss_qualifier.resources.communications import AuthAdapterResource


class DSSInstanceSpecification(ImplicitDict):

    participant_id: ParticipantID
    """ID of the USS responsible for this DSS instance"""

    rid_version: RIDVersion
    """Version of ASTM F3411 implemented by this DSS instance"""

    base_url: str
    """Base URL for the DSS instance according to the ASTM F3411 API appropriate to the specified rid_version"""

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        try:
            urlparse(self.base_url)
        except ValueError:
            raise ValueError("DSSInstanceConfiguration.base_url must be a URL")


class DSSInstance(object):
    participant_id: ParticipantID
    rid_version: RIDVersion
    base_url: str
    client: infrastructure.UTMClientSession

    def __init__(
        self,
        participant_id: ParticipantID,
        base_url: str,
        rid_version: RIDVersion,
        auth_adapter: infrastructure.AuthAdapter,
    ):
        self.participant_id = participant_id
        self.base_url = base_url
        self.rid_version = rid_version
        self.client = infrastructure.UTMClientSession(base_url, auth_adapter)

    def is_same_as(self, other: DSSInstance) -> bool:
        return (
            self.participant_id == other.participant_id
            and self.rid_version == other.rid_version
            and self.base_url == other.base_url
        )


class DSSInstanceResource(Resource[DSSInstanceSpecification]):
    dss_instance: DSSInstance

    def __init__(
        self,
        specification: DSSInstanceSpecification,
        resource_origin: str,
        auth_adapter: AuthAdapterResource,
    ):
        super(DSSInstanceResource, self).__init__(specification, resource_origin)

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
            auth_adapter.adapter,
        )

    @classmethod
    def from_dss_instance(cls, dss_instance: DSSInstance) -> DSSInstanceResource:
        self = cls.__new__(cls)
        self.dss_instance = dss_instance
        return self


class DSSInstancesSpecification(ImplicitDict):
    dss_instances: List[DSSInstanceSpecification]


class DSSInstancesResource(Resource[DSSInstancesSpecification]):
    dss_instances: List[DSSInstance]

    def __init__(
        self,
        specification: DSSInstancesSpecification,
        resource_origin: str,
        auth_adapter: AuthAdapterResource,
    ):
        super(DSSInstancesResource, self).__init__(specification, resource_origin)
        self.dss_instances = [
            DSSInstanceResource(
                s, f"instance {i + 1} in {resource_origin}", auth_adapter
            ).dss_instance
            for i, s in enumerate(specification.dss_instances)
        ]
