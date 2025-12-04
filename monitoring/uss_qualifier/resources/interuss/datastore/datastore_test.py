import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from . import CockroachDBNode, YugabyteDBNode


@pytest.fixture(scope="module")
def good_cockroach(request):
    server = DockerContainer(
        image="cockroachdb/cockroach:v24.1.3",
        ports=[26257],
        command="start-single-node",
    )
    server.waiting_for(LogMessageWaitStrategy("start_node_query"))
    server.start()

    return CockroachDBNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(26257)
    )


@pytest.fixture(scope="module")
def no_ssl_cockroach(request):
    server = DockerContainer(
        image="cockroachdb/cockroach:v24.1.3",
        ports=[26257],
        command="start-single-node --insecure",
    )
    server.waiting_for(LogMessageWaitStrategy("start_node_query"))
    server.start()

    return CockroachDBNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(26257)
    )


@pytest.fixture(scope="module")
def old_ssl_cockroach(request):
    server = DockerContainer(
        image="interuss/insecurecockroach:latest",
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
        image="mcuoorb/ytest:v010",  # TODO: Replace me when official images are released
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
        image="yugabytedb/yugabyte:2.25.2.0-b359",
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
def no_ssl_yugabyte(request):
    server = DockerContainer(
        image="yugabytedb/yugabyte:2.25.2.0-b359",
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
    assert is_reachable


def test_datastoredbmode_connect_good_yugabyte(good_yugabyte):
    is_reachable, _ = good_yugabyte.is_reachable()
    assert is_reachable


def test_datastoredbmode_connect_no_ssl_cockroach(no_ssl_cockroach):
    is_reachable, _ = no_ssl_cockroach.is_reachable()
    assert is_reachable


def test_datastoredbmode_connect_no_ssl_yugabyte(no_ssl_yugabyte):
    is_reachable, _ = no_ssl_yugabyte.is_reachable()
    assert is_reachable


def test_datastoredbmode_connect_old_ssl_cockroach(old_ssl_cockroach):
    is_reachable, _ = old_ssl_cockroach.is_reachable()
    assert is_reachable


def test_datastoredbmode_secure_mode_good_cockroach(good_cockroach):
    is_secure, _ = good_cockroach.runs_in_secure_mode()
    assert is_secure


def test_datastoredbmode_secure_mode_good_yugabyte(good_yugabyte):
    is_secure, e = good_yugabyte.runs_in_secure_mode()
    assert not e, is_secure


def test_datastoredbmode_secure_mode_yugabyte_without_client_auth(
    yugabyte_without_client_auth,
):
    is_secure, _ = yugabyte_without_client_auth.runs_in_secure_mode()
    assert not is_secure


def test_datastoredbmode_secure_mode_no_ssl_cockroach(no_ssl_cockroach):
    is_secure, _ = no_ssl_cockroach.runs_in_secure_mode()
    assert not is_secure


def test_datastoredbmode_secure_mode_no_ssl_yugabyte(no_ssl_yugabyte):
    is_secure, _ = no_ssl_yugabyte.runs_in_secure_mode()
    assert not is_secure


def test_datastoredbmode_secure_mode_old_ssl_cockroach(old_ssl_cockroach):
    is_secure, _ = old_ssl_cockroach.runs_in_secure_mode()
    assert is_secure


def test_datastoredbmode_reject_legacy_good_cockroach(good_cockroach):
    legacy_rejected, _ = good_cockroach.legacy_ssl_version_rejected()
    assert legacy_rejected


def test_datastoredbmode_reject_legacy_good_yugabyte(good_yugabyte):
    legacy_rejected, _ = good_yugabyte.legacy_ssl_version_rejected()
    assert legacy_rejected


def test_datastoredbmode_reject_legacy_old_ssl_cockroach(old_ssl_cockroach):
    legacy_rejected, _ = old_ssl_cockroach.legacy_ssl_version_rejected()
    assert not legacy_rejected
