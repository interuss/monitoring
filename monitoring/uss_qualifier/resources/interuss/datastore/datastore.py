from __future__ import annotations

import socket
import ssl
from abc import ABC, abstractmethod

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

    is_yugabyte: bool = False
    """True if DatastoreDB node is a YugabyteDB node."""

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
        if self._specification.is_yugabyte:
            return YugabyteDBNode(
                self._specification.participant_id,
                self._specification.host,
                self._specification.port,
            )
        return CockroachDBNode(
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


class DatastoreDBNode(ABC):
    _NOT_IMPLEMENTED_MSG = "All methods of base DatastoreDBNode class must be implemented by each specific subclass"

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

    @abstractmethod
    def is_reachable(self) -> tuple[bool, Exception | None]:
        """Returns True if the node is reachable."""
        raise NotImplementedError(DatastoreDBNode._NOT_IMPLEMENTED_MSG)

    @abstractmethod
    def no_ssl_rejected(self) -> tuple[bool, Exception | None]:
        """Returns True if the node rejects cleartext communications."""
        raise NotImplementedError(DatastoreDBNode._NOT_IMPLEMENTED_MSG)

    @abstractmethod
    def unauthenticated_rejected(self) -> tuple[bool, Exception | None]:
        """Returns True if the node rejects unauthenticated communications."""
        raise NotImplementedError(DatastoreDBNode._NOT_IMPLEMENTED_MSG)

    @abstractmethod
    def legacy_ssl_version_rejected(self) -> tuple[bool, Exception | None]:
        """Returns True if the node rejects the usage of the legacy cryptographic protocols TLSv1 and TLSv1.1."""
        raise NotImplementedError(DatastoreDBNode._NOT_IMPLEMENTED_MSG)


class CockroachDBNode(DatastoreDBNode):
    def connect(self, **kwargs) -> psycopg.Connection:
        return psycopg.connect(
            host=self.host,
            port=self.port,
            user="dummy",
            **kwargs,
        )

    def is_reachable(self) -> tuple[bool, Exception | None]:
        """
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

    def runs_in_secure_mode(self) -> tuple[bool, Exception | None]:
        """
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

    def no_ssl_rejected(self) -> tuple[bool, Exception | None]:
        return self.runs_in_secure_mode()

    def unauthenticated_rejected(self) -> tuple[bool, Exception | None]:
        return self.runs_in_secure_mode()

    def legacy_ssl_version_rejected(self) -> tuple[bool, Exception | None]:
        """
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


class YugabyteDBNode(DatastoreDBNode):
    def _connect(self) -> socket.socket:
        return socket.create_connection(
            (self.host, self.port),
            timeout=5,
        )

    def is_reachable(self) -> tuple[bool, Exception | None]:
        """This is detected by attempting to open a socket with the node."""
        try:
            sock = self._connect()
            sock.close()
            return True, None
        except (TimeoutError, ConnectionError) as e:
            return False, e

    def runs_in_secure_mode(self) -> tuple[bool, Exception | None]:
        """
        Returns True is node runs in secure mode. If False, returns an exception describing the issue.
        Expects node to be reachable (see is_reachable).
        Secure mode is detected by:
        1) attempting to establish a connection with the node in cleartext; and then
        2) attempting to establish a connection with the node using TLS but without authentication using a client certificate.
        """
        secure_without_ssl, e_without_ssl = self._attempt_insecure_request(
            with_ssl=False
        )
        # secure_without_ssl, e_without_ssl = True, None TODO: handle ConnectionResetByPeer when doing recv? or not?
        secure_with_ssl, e_with_ssl = self._attempt_insecure_request(with_ssl=True)
        if secure_without_ssl and secure_with_ssl:
            return True, None

        err_msg = "Node is not in secure mode:\n"
        if e_without_ssl:
            err_msg += f"Request without SSL: {e_without_ssl}\n"
        if e_with_ssl:
            err_msg += f"Request with SSL: {e_with_ssl}\n"
        return False, Exception(err_msg)

    @classmethod
    def _build_dummy_rpc_request(cls):
        """Builds an RPC request for service 'yb.master.MasterService', method 'GetMasterRegistration' with call ID '5'.
        Reference: https://gruchalski.com/posts/2022-02-12-a-brief-look-at-yugabytedb-rpc-api/"""

        return bytes.fromhex(
            "594201"  # 'YB1' preamble
            "0000003a"  # message byte length
            "38"  # request header protobuf message length
            "0805"  # field 1: call_id
            "12300a1779622e6d61737465722e4d61737465725365727669636512154765744d6173746572526567697374726174696f6e"  # field 2: remote_method (service_name = 'yb.master.MasterService', method_name = 'GetMasterRegistration')
            "18e0d403"  # field 3: timeout_millis
            "00"  # request payload protobuf message length (no payload)
        )

    def _attempt_insecure_request(
        self, with_ssl: bool
    ) -> tuple[bool, Exception | None]:
        sock = self._connect()  # we expect node to be reachable
        if with_ssl:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            try:
                sock = ctx.wrap_socket(sock)
                sock.do_handshake(block=True)
            except ssl.SSLError as e:
                # if we fail to create the SSL context: insecure
                sock.close()
                return False, e

        sock.sendall(self._build_dummy_rpc_request())
        msg_size_bytes = sock.recv(4)  # message byte length (32-bits integer)
        if len(msg_size_bytes) == 0:
            # server closed connection upon receiving a valid RPC through insecure channel: secure
            sock.close()
            return True, None

        # server did not close connection: read response, msg_bytes is expected to look like:
        # 04 # protobuf message length (response header)
        # 0805 # field 1: call_id
        # 1000 # field 2: is_error
        # 8701 # protobuf message length (response payload)
        # 0a34... # protobuf response payload
        msg_size = int.from_bytes(msg_size_bytes, byteorder="big")
        msg_bytes = sock.recv(msg_size)
        sock.close()
        return False, Exception(
            f"Received RPC response from node, hex: {bytes.hex(msg_bytes)}"
        )

    def no_ssl_rejected(self) -> tuple[bool, Exception | None]:
        return self._attempt_insecure_request(with_ssl=False)

    def unauthenticated_rejected(self) -> tuple[bool, Exception | None]:
        return self._attempt_insecure_request(with_ssl=True)

    def legacy_ssl_version_rejected(self) -> tuple[bool, Exception | None]:
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
                sock.sendall(_build_client_hello())
                data = sock.recv(1024)

                if not data:
                    return True, None  # Server will close the connection without reply

                return _is_protocol_failure(data), None
        except Exception as e:
            return False, e
