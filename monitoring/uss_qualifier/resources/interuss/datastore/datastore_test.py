import os

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from . import CockroachDBNode, YugabyteDBNode
from .datastore import (
    DatastoreDBNodeResource,
    DatastoreDBNodeSpecification,
    RaftNode,
    self_signed_certificate,
)

COCKROACHDB_IMAGE = "cockroachdb/cockroach:v24.1.3"
INSECURE_COCKROACHDB_IMAGE = "interuss/insecurecockroach:latest"
YUGABYTE_IMAGE = "interuss/yugabyte:2025.1.2.1-interuss"
INSECURE_YUGABYTE_IMAGE = "yugabytedb/yugabyte:2.25.2.0-b359"
DSS_IMAGE = os.environ.get("DSS_IMAGE", "interuss/dss:latest")
RAFT_COMMAND = "core-service -store_type raft -raft_node_id 1 -raft_datadir /tmp/raft -public_key_files /test-certs/auth2.pem -accepted_jwt_audiences localhost -public_endpoint http://localhost -locality test"


@pytest.fixture(scope="module")
def good_cockroach(request):
    server = DockerContainer(
        image=COCKROACHDB_IMAGE,
        ports=[26257],
        command="start-single-node",
    )
    server.waiting_for(LogMessageWaitStrategy("start_node_query"))
    server.start()

    yield CockroachDBNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(26257)
    )
    server.stop()


@pytest.fixture(scope="module")
def not_running_cockroach(request):
    return CockroachDBNode("test", "127.0.0.1", 1)


@pytest.fixture(scope="module")
def not_running_yugabyte(request):
    return YugabyteDBNode("test", "127.0.0.1", 1)


@pytest.fixture(scope="module")
def no_tls_cockroach(request):
    server = DockerContainer(
        image=COCKROACHDB_IMAGE,
        ports=[26257],
        command="start-single-node --insecure",
    )
    server.waiting_for(LogMessageWaitStrategy("start_node_query"))
    server.start()

    yield CockroachDBNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(26257)
    )
    server.stop()


@pytest.fixture(scope="module")
def old_tls_cockroach(request):
    server = DockerContainer(
        image=INSECURE_COCKROACHDB_IMAGE,
        ports=[26257],
        command="start-single-node",
    )
    server.waiting_for(LogMessageWaitStrategy("start_node_query"))
    server.start()

    yield CockroachDBNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(26257)
    )
    server.stop()


@pytest.fixture(scope="module")
def good_yugabyte(request):
    server = DockerContainer(
        image=YUGABYTE_IMAGE,
        ports=[7100],
        command='bash -c "bin/yugabyted cert generate_server_certs --base_dir /yugabyte/certs --hostnames `hostname` && bin/yugabyted start --secure --certs_dir=/yugabyte/certs/generated_certs/`hostname` --advertise_address=`hostname` --background=false --tserver_flags=node_to_node_encryption_use_client_certificates=true --master_flags=node_to_node_encryption_use_client_certificates=true,use_node_to_node_encryption=true"',
    )
    server.waiting_for(
        LogMessageWaitStrategy("Data placement constraint successfully verified")
    )
    server.start()

    yield YugabyteDBNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(7100)
    )
    server.stop()


@pytest.fixture(scope="module")
def yugabyte_without_client_auth(request):
    server = DockerContainer(
        image=INSECURE_YUGABYTE_IMAGE,
        ports=[7100],
        command='bash -c "bin/yugabyted cert generate_server_certs --base_dir /yugabyte/certs --hostnames `hostname` && bin/yugabyted start --secure --certs_dir=/yugabyte/certs/generated_certs/`hostname` --advertise_address=`hostname` --background=false"',
    )
    server.waiting_for(
        LogMessageWaitStrategy("Data placement constraint successfully verified")
    )
    server.start()

    yield YugabyteDBNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(7100)
    )
    server.stop()


@pytest.fixture(scope="module")
def no_tls_yugabyte(request):
    server = DockerContainer(
        image=INSECURE_YUGABYTE_IMAGE,
        ports=[7100],
        command="bin/yugabyted start --background=false",
    )
    server.waiting_for(
        LogMessageWaitStrategy("Data placement constraint successfully verified")
    )
    server.start()

    yield YugabyteDBNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(7100)
    )
    server.stop()


def test_datastoredbmode_connect_good_cockroach(good_cockroach):
    is_reachable, _ = good_cockroach.is_reachable()
    assert is_reachable, "Running CockroachDB server shall be reachable"


def test_datastoredbmode_connect_good_yugabyte(good_yugabyte):
    is_reachable, _ = good_yugabyte.is_reachable()
    assert is_reachable, "Running Yugabyte server shall be reachable"


def test_datastoredbmode_connect_yugabyte_without_client_auth(
    yugabyte_without_client_auth,
):
    is_reachable, _ = yugabyte_without_client_auth.is_reachable()
    assert is_reachable, "Running Yugabyte server shall be reachable"


def test_datastoredbmode_connect_no_tls_cockroach(no_tls_cockroach):
    is_reachable, _ = no_tls_cockroach.is_reachable()
    assert is_reachable, "Running CockroachDB server shall be reachable"


def test_datastoredbmode_connect_no_tls_yugabyte(no_tls_yugabyte):
    is_reachable, _ = no_tls_yugabyte.is_reachable()
    assert is_reachable, "Running Yugabyte server shall be reachable"


def test_datastoredbmode_connect_not_running_cockroach(not_running_cockroach):
    is_reachable, _ = not_running_cockroach.is_reachable()
    assert not is_reachable, "Non-running CockroachDB server shall not be reachable"


def test_datastoredbmode_connect_not_running_yugabyte(not_running_yugabyte):
    is_reachable, _ = not_running_yugabyte.is_reachable()
    assert not is_reachable, "Non-running Yugabyte server shall not be reachable"


def test_datastoredbmode_no_tls_rejected_good_cockroach(good_cockroach):
    no_tls_rejected, _ = good_cockroach.no_tls_rejected()
    assert no_tls_rejected, (
        "Nominal CockroachDB server shall reject connections without TLS"
    )


def test_datastoredbmode_no_tls_rejected_good_yugabyte(good_yugabyte):
    no_tls_rejected, _ = good_yugabyte.no_tls_rejected()
    assert no_tls_rejected, (
        "Nominal Yugabyte server shall reject connections without TLS"
    )


def test_datastoredbmode_no_tls_rejected_yugabyte_without_client_auth(
    yugabyte_without_client_auth,
):
    no_tls_rejected, _ = yugabyte_without_client_auth.no_tls_rejected()
    assert no_tls_rejected, (
        "Yugabyte server without mTLS shall still reject connections without TLS"
    )


def test_datastoredbmode_no_tls_rejected_no_tls_cockroach(no_tls_cockroach):
    no_tls_rejected, _ = no_tls_cockroach.no_tls_rejected()
    assert not no_tls_rejected, (
        "CockroachDB server, with TLS disabled, shall not reject connections without TLS"
    )


def test_datastoredbmode_no_tls_rejected_no_tls_yugabyte(no_tls_yugabyte):
    no_tls_rejected, _ = no_tls_yugabyte.no_tls_rejected()
    assert not no_tls_rejected, (
        "Yugabyte server, with TLS disabled, shall not reject connections without TLS"
    )


def test_datastoredbmode_no_tls_rejected_old_tls_cockroach(old_tls_cockroach):
    no_tls_rejected, _ = old_tls_cockroach.no_tls_rejected()
    assert no_tls_rejected, (
        "CockroachDB server, with old TLS version enabled, shall not reject connections without TLS"
    )


def test_datastoredbmode_unauthenticated_rejected_good_cockroach(good_cockroach):
    unauthenticated_rejected, _ = good_cockroach.unauthenticated_rejected()
    assert unauthenticated_rejected, (
        "Nominal CockroachDB server shall reject unauthenticated connections"
    )


def test_datastoredbmode_unauthenticated_rejected_good_yugabyte(good_yugabyte):
    unauthenticated_rejected, _ = good_yugabyte.unauthenticated_rejected()
    assert unauthenticated_rejected, (
        "Nominal Yugabyte server shall reject unauthenticated connections"
    )


def test_datastoredbmode_unauthenticated_rejected_yugabyte_without_client_auth(
    yugabyte_without_client_auth,
):
    unauthenticated_rejected, _ = (
        yugabyte_without_client_auth.unauthenticated_rejected()
    )
    assert not unauthenticated_rejected, (
        "Yugabyte without mTLS shall accept unauthenticated requests (since mTLS is the authentication method)"
    )


def test_datastoredbmode_unauthenticated_rejected_no_tls_cockroach(no_tls_cockroach):
    unauthenticated_rejected, _ = no_tls_cockroach.unauthenticated_rejected()
    assert unauthenticated_rejected, (
        "CockroachDB server, with TLS disabled, shall reject authenticated requests"
    )


def test_datastoredbmode_unauthenticated_rejected_no_tls_yugabyte(no_tls_yugabyte):
    unauthenticated_rejected, _ = no_tls_yugabyte.unauthenticated_rejected()
    assert not unauthenticated_rejected, (
        "Yugabyte without TLS shall accept unauthenticated requests (since mTLS is the authentication method)"
    )


def test_datastoredbmode_unauthenticated_rejected_old_tls_cockroach(old_tls_cockroach):
    unauthenticated_rejected, _ = old_tls_cockroach.unauthenticated_rejected()
    assert unauthenticated_rejected, (
        "CockroachDB server, with old TLS version enabled, shall reject authenticated requests"
    )


def test_datastoredbmode_reject_legacy_good_cockroach(good_cockroach):
    legacy_rejected, _ = good_cockroach.legacy_tls_version_rejected()
    assert legacy_rejected, (
        "Nominal CockroachDB server shall reject connections wtih legacy TLS version"
    )


def test_datastoredbmode_reject_legacy_good_yugabyte(good_yugabyte):
    legacy_rejected, _ = good_yugabyte.legacy_tls_version_rejected()
    assert legacy_rejected, (
        "Nominal Yugabyte server shall reject connections wtih legacy TLS version"
    )


def test_datastoredbmode_reject_legacy_yugabyte_without_client_auth(
    yugabyte_without_client_auth,
):
    legacy_rejected, _ = yugabyte_without_client_auth.legacy_tls_version_rejected()
    assert legacy_rejected, (
        "Yugabyte without mTLS shall reject connections wtih legacy TLS version"
    )


def test_datastoredbmode_reject_legacy_old_tls_cockroach(old_tls_cockroach):
    legacy_rejected, _ = old_tls_cockroach.legacy_tls_version_rejected()
    assert not legacy_rejected, (
        "CockroachDB server, with old TLS version enabled, shall not reject connections wtih legacy TLS versions"
    )


@pytest.fixture(scope="module")
def good_raft(request):
    cert, key = self_signed_certificate()
    server = (
        DockerContainer(
            image=DSS_IMAGE,
            ports=[9500],
            command=f"sh -c 'printenv CERT > /tmp/node.crt && printenv KEY > /tmp/node.key && {RAFT_COMMAND} -raft_peers 1=https://localhost:9500 -raft_tls_cert_file /tmp/node.crt -raft_tls_key_file /tmp/node.key -raft_tls_ca_file /tmp/node.crt'",
        )
        .with_env("CERT", cert.decode())
        .with_env("KEY", key.decode())
    )
    server.waiting_for(LogMessageWaitStrategy("raft listener started"))
    server.start()

    yield RaftNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(9500)
    )
    server.stop()


@pytest.fixture(scope="module")
def no_tls_raft(request):
    server = DockerContainer(
        image=DSS_IMAGE,
        ports=[9500],
        command=f"{RAFT_COMMAND} -raft_peers 1=http://localhost:9500 -raft_insecure",
    )
    server.waiting_for(LogMessageWaitStrategy("raft listener started"))
    server.start()

    yield RaftNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(9500)
    )
    server.stop()


@pytest.fixture(scope="module")
def not_running_raft(request):
    return RaftNode("test", "127.0.0.1", 1)


def test_datastoredbmode_connect_good_raft(good_raft):
    is_reachable, _ = good_raft.is_reachable()
    assert is_reachable, "Running Raft node shall be reachable"


def test_datastoredbmode_connect_no_tls_raft(no_tls_raft):
    is_reachable, _ = no_tls_raft.is_reachable()
    assert is_reachable, "Running Raft node shall be reachable"


def test_datastoredbmode_connect_not_running_raft(not_running_raft):
    is_reachable, _ = not_running_raft.is_reachable()
    assert not is_reachable, "Non-running Raft node shall not be reachable"


def test_datastoredbmode_no_tls_rejected_good_raft(good_raft):
    no_tls_rejected, _ = good_raft.no_tls_rejected()
    assert no_tls_rejected, "Nominal Raft node shall reject connections without TLS"


def test_datastoredbmode_no_tls_rejected_no_tls_raft(no_tls_raft):
    no_tls_rejected, _ = no_tls_raft.no_tls_rejected()
    assert not no_tls_rejected, (
        "Raft node, with TLS disabled, shall not reject connections without TLS"
    )


def test_datastoredbmode_unauthenticated_rejected_good_raft(good_raft):
    unauthenticated_rejected, _ = good_raft.unauthenticated_rejected()
    assert unauthenticated_rejected, (
        "Nominal Raft node shall reject connections without a trusted certificate"
    )


def test_datastoredbmode_unauthenticated_rejected_no_tls_raft(no_tls_raft):
    unauthenticated_rejected, _ = no_tls_raft.unauthenticated_rejected()
    assert not unauthenticated_rejected, (
        "Raft node, with TLS disabled, shall not reject unauthenticated connections"
    )


def test_datastoredbmode_reject_legacy_good_raft(good_raft):
    legacy_rejected, _ = good_raft.legacy_tls_version_rejected()
    assert legacy_rejected, (
        "Nominal Raft node shall reject connections with legacy TLS version"
    )


def test_datastoredbmode_reject_legacy_no_tls_raft(no_tls_raft):
    legacy_rejected, _ = no_tls_raft.legacy_tls_version_rejected()
    assert not legacy_rejected, (
        "Raft node, with TLS disabled, shall not reject connections with legacy TLS version"
    )


def test_datastoredbmode_yugabyte_and_raft_rejected():
    specification = DatastoreDBNodeSpecification(
        participant_id="test", host="127.0.0.1", port=1, is_yugabyte=True, is_raft=True
    )
    with pytest.raises(ValueError):
        DatastoreDBNodeResource(specification, "test")
