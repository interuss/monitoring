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

    local_debug: Optional[bool]
    """Whether this DSS instance is running locally for debugging or development purposes. Mostly used for relaxing
    constraints around encryption.
    Assumed to be true if left unspecified and has_private_address is true, otherwise defaults to false
    """

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        if not self.has_field_with_value("local_debug"):
            if self.has_field_with_value("has_private_address") and self.get(
                "has_private_address"
            ):
                self.local_debug = True
            else:
                self.local_debug = False
        try:
            urlparse(self.base_url)
        except ValueError:
            raise ValueError("DSSInstanceConfiguration.base_url must be a URL")


class DSSInstance(object):
    participant_id: ParticipantID
    rid_version: RIDVersion
    base_url: str
    has_private_address: bool = False
    local_debug: bool = False
    client: infrastructure.UTMClientSession

    def __init__(
        self,
        participant_id: ParticipantID,
        base_url: str,
        has_private_address: Optional[bool],
        local_debug: Optional[bool],
        rid_version: RIDVersion,
        auth_adapter: infrastructure.AuthAdapter,
    ):
        self.participant_id = participant_id
        self.base_url = base_url
        self.rid_version = rid_version
        self.client = infrastructure.UTMClientSession(base_url, auth_adapter)

        if has_private_address is not None:
            self.has_private_address = has_private_address
            self.local_debug = True
        if local_debug is not None:
            self.local_debug = local_debug

    def is_same_as(self, other: DSSInstance) -> bool:
        return (
            self.participant_id == other.participant_id
            and self.rid_version == other.rid_version
            and self.base_url == other.base_url
            and self.has_private_address == other.has_private_address
            and self.local_debug == other.local_debug
        )


class DSSInstanceResource(Resource[DSSInstanceSpecification]):
    dss_instance: DSSInstance

    def __init__(
        self, specification: DSSInstanceSpecification, auth_adapter: AuthAdapterResource
    ):
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
            specification.has_private_address,
            specification.local_debug,
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
            DSSInstanceResource(s, auth_adapter).dss_instance
            for s in specification.dss_instances
        ]
