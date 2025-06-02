from __future__ import annotations

from typing import List, Optional, Tuple

import psycopg
from implicitdict import ImplicitDict

from monitoring.uss_qualifier.resources.resource import Resource


class DatastoreDBNodeSpecification(ImplicitDict):
    participant_id: str
    """ID of the USS responsible for this DatastoreDB node"""

    host: str
    """Host where the DatastoreDB node is reachable."""

    port: int
    """Port to which DatastoreDB node is listening to."""

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)


class DatastoreDBNodeResource(Resource[DatastoreDBNodeSpecification]):
    _specification: DatastoreDBNodeSpecification

    def __init__(
        self,
        specification: DatastoreDBNodeSpecification,
        resource_origin: str,
    ):
        super(DatastoreDBNodeResource, self).__init__(specification, resource_origin)
        self._specification = specification

    def get_client(self) -> DatastoreDBNode:
        return DatastoreDBNode(
            self._specification.participant_id,
            self._specification.host,
            self._specification.port,
        )

    def is_same_as(self, other: DatastoreDBNodeResource) -> bool:
        return self._specification == other._specification

    @property
    def participant_id(self) -> str:
        return self._specification.participant_id


class DatastoreDBClusterSpecification(ImplicitDict):
    nodes: List[DatastoreDBNodeSpecification]


class DatastoreDBClusterResource(Resource[DatastoreDBClusterSpecification]):
    nodes: List[DatastoreDBNodeResource]

    def __init__(
        self,
        specification: DatastoreDBClusterSpecification,
        resource_origin: str,
    ):
        super(DatastoreDBClusterResource, self).__init__(specification, resource_origin)
        self.nodes = [
            DatastoreDBNodeResource(
                specification=s, resource_origin=f"node {i + 1} in {resource_origin}"
            )
            for i, s in enumerate(specification.nodes)
        ]


class DatastoreDBNode(object):
    participant_id: str
    host: str
    port: int

    def __init__(
        self,
        participant_id: str,
        host: str,
        port: int,
    ):
        self.participant_id = participant_id
        self.host = host
        self.port = port

    def connect(self, **kwargs) -> psycopg.Connection:
        return psycopg.connect(
            host=self.host,
            port=self.port,
            user="dummy",
            **kwargs,
        )

    def is_reachable(self) -> Tuple[bool, Optional[psycopg.Error]]:
        """
        Returns True if the node is reachable.
        This is detected by attempting to establish a connection with the node
        not requiring encryption and validating either 1) that the connection
        fails with the error message reporting that the authentication failed;
        or 2) that the connection succeeds.
        """
        try:
            c = self.connect(sslmode="allow", require_auth="password", password="dummy")
            c.close()
        except psycopg.OperationalError as e:
            err_msg = str(e)
            is_reachable = "password authentication failed" in err_msg
            return is_reachable, e
        return True, None

    def runs_in_secure_mode(self) -> Tuple[bool, Optional[psycopg.Error]]:
        """
        Returns True if the node is running in secure mode.
        This is detected by attempting to establish a connection with the node
        in insecure mode and validating that the connection fails with the error
        message reporting that the node is running in secure mode.
        """
        try:
            c = self.connect(sslmode="disable")
            c.close()
        except psycopg.OperationalError as e:
            err_msg = str(e)
            secure_mode = "node is running secure mode" in err_msg
            return secure_mode, e
        return False, None

    def legacy_ssl_version_rejected(self) -> Tuple[bool, Optional[psycopg.Error]]:
        """
        Returns True if the node rejects the usage of the legacy cryptographic
        protocols TLSv1 and TLSv1.1.
        This is detected by attempting to establish a connection with the node
        forcing the client to use a TLS version < 1.2 and validating that the
        connection fails with the expected error message.
        """
        try:
            c = self.connect(
                sslmode="require",
                ssl_min_protocol_version="TLSv1",
                ssl_max_protocol_version="TLSv1.1",
            )
            c.close()
        except psycopg.OperationalError as e:
            err_msg = str(e)
            legacy_rejected = "tlsv1 alert protocol version" in err_msg
            return legacy_rejected, e
        return False, None
