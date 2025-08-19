from __future__ import annotations

import socket

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
        super().__init__(specification, resource_origin)
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
    nodes: list[DatastoreDBNodeSpecification]


class DatastoreDBClusterResource(Resource[DatastoreDBClusterSpecification]):
    nodes: list[DatastoreDBNodeResource]

    def __init__(
        self,
        specification: DatastoreDBClusterSpecification,
        resource_origin: str,
    ):
        super().__init__(specification, resource_origin)
        self.nodes = [
            DatastoreDBNodeResource(
                specification=s, resource_origin=f"node {i + 1} in {resource_origin}"
            )
            for i, s in enumerate(specification.nodes)
        ]


class DatastoreDBNode:
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

    def is_reachable(self) -> tuple[bool, psycopg.Error | None]:
        """
        Returns True if the node is reachable.
        This is detected by attempting to establish a connection with the node
        not requiring encryption and validating either 1) that the connection
        fails with the error message reporting that the authentication failed;
        or 2) that the connection succeeds.
        """
        try:
            c = self.connect(
                sslmode="prefer", require_auth="password", password="dummy"
            )
            c.close()
        except psycopg.OperationalError as e:
            err_msg = str(e)
            # First message is returned if password authentication is enabled
            # (CockroachDB), second one if not (Yugabyte use certificates)
            is_reachable = (
                "password authentication failed" in err_msg
                or "server did not complete authentication" in err_msg
                or "server requested a hashed password" in err_msg
            )
            return is_reachable, e
        return True, None

    def runs_in_secure_mode(self) -> tuple[bool, psycopg.Error | None]:
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
            # First message is returned by CockroachDB, second one by Yugabyte
            # (No hba entries for authentication outside SSL)
            secure_mode = (
                "node is running secure mode" in err_msg
                or "no pg_hba.conf entry for host" in err_msg
            )
            return secure_mode, e
        return False, None

    def legacy_ssl_version_rejected(self) -> tuple[bool, psycopg.Error | None]:
        """
        Returns True if the node rejects the usage of the legacy cryptographic
        protocols TLSv1 and TLSv1.1.
        This is detected by attempting to establish a connection with the node
        forcing the client to use a TLS version < 1.2 and validating that the
        connection fails with the expected error message.

        Modern libraries and Python have dropped support for TLS versions older than 1.2, as these are now considered legacy.

        To be able to test those old protocols, we manually send TLS packets (captured from legacy code) and parse the result.
        Parsing is limited, but should be good enough for our cases.
        """

        def _build_client_hello():
            """Builds a client hello"""

            return bytes.fromhex(
                "16"  # Handshake
                "0301"  # TLS Version: 1.0
                "0063"  # Length
                "01"  # Handshake type: Client hello
                "00005f"  # Length
                "0302"  # TLS Version: 1.1
                "4895335bae2d2d929e34bdd5ccc89d800807bb01bbaaa7bf86efbb83a9249206"  # Random value
                "00"  # Session ID Length
                "0012"  # Cipher suite Length
                "c00ac0140039c009c01300330035002f00ff"  # Cipher suites
                "01"  # Compression method length
                "00"  # No compression
                "0024"  # Extentions length
                "000b000403000102000a000c000a001d0017001e00190018002300000016000000170000"  # Extensions
            )

        def _is_protocol_failure(data):
            """Tests whether the server sends a protocol failure."""
            # Format:
            # 15     TLS Alert
            # 03 01  TLS Version (Ignored)
            # 00 02  Length (Ignored)
            # 02     Level: Fatal (Ignored)
            # 46     Description: Protocol version

            content_type = data[0]
            alert_description = data[6]

            return content_type == 0x15 and alert_description == 0x46

        try:
            with socket.create_connection((self.host, self.port), timeout=5) as sock:
                sock.sendall(bytes.fromhex("0000000804d2162f"))  # Postgres hello
                sock.recv(16)
                sock.sendall(_build_client_hello())
                data = sock.recv(1024)

                if not data:
                    return False, "No response from server"

                return _is_protocol_failure(data), None
        except Exception as e:
            return False, str(e)
