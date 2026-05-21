import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from . import CockroachDBNode, YugabyteDBNode

COCKROACHDB_IMAGE = "cockroachdb/cockroach:v24.1.3"
INSECURE_COCKROACHDB_IMAGE = "interuss/insecurecockroach:latest"
YUGABYTE_IMAGE = "interuss/yugabyte:2025.1.2.1-interuss"
INSECURE_YUGABYTE_IMAGE = "yugabytedb/yugabyte:2.25.2.0-b359"


@pytest.fixture(scope="module")
def good_cockroach(request):
    server = DockerContainer(
        image=COCKROACHDB_IMAGE,
        ports=[26257],
        command="start-single-node",
    )
    server.waiting_for(LogMessageWaitStrategy("start_node_query"))
    server.start()

    return CockroachDBNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(26257)
    )


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

    return CockroachDBNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(26257)
    )


@pytest.fixture(scope="module")
def old_tls_cockroach(request):
    server = DockerContainer(
        image=INSECURE_COCKROACHDB_IMAGE,
        ports=[26257],
        command="start-single-node",
    )
    server.waiting_for(LogMessageWaitStrategy("start_node_query"))
    server.start()

    return CockroachDBNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(26257)
    )


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

    return YugabyteDBNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(7100)
    )


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

    return YugabyteDBNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(7100)
    )


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

    return YugabyteDBNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(7100)
    )


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
