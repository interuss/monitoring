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

    has_private_address: Optional[bool]
    """Whether this DSS instance is expected to have a private address that is not publicly addressable."""

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
    has_private_address: bool = False
    client: infrastructure.UTMClientSession

    def __init__(
        self,
        participant_id: ParticipantID,
        base_url: str,
        has_private_address: Optional[bool],
        rid_version: RIDVersion,
        auth_adapter: infrastructure.AuthAdapter,
    ):
        self.participant_id = participant_id
        self.base_url = base_url
        self.rid_version = rid_version
        self.client = infrastructure.UTMClientSession(base_url, auth_adapter)

        if has_private_address is not None:
            self.has_private_address = has_private_address


class DSSInstanceResource(Resource[DSSInstanceSpecification]):
    dss_instance: DSSInstance

    def __init__(
        self, specification: DSSInstanceSpecification, auth_adapter: AuthAdapterResource
    ):
        self.dss_instance = DSSInstance(
            specification.participant_id,
            specification.base_url,
            specification.has_private_address,
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
        auth_adapter: AuthAdapterResource,
    ):
        self.dss_instances = [
            DSSInstance(
                s.participant_id,
                s.base_url,
                s.has_private_address,
                s.rid_version,
                auth_adapter.adapter,
            )
            for s in specification.dss_instances
        ]
