import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from . import DatastoreDBNode


@pytest.fixture(scope="module")
def good_cockroach(request):
    server = DockerContainer(
        image="cockroachdb/cockroach:v24.1.3",
        ports=[26257],
        command="start-single-node",
    )
    server.start()
    wait_for_logs(server, "start_node_query")

    return DatastoreDBNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(26257)
    )


@pytest.fixture(scope="module")
def no_ssl_cockroach(request):
    server = DockerContainer(
        image="cockroachdb/cockroach:v24.1.3",
        ports=[26257],
        command="start-single-node --insecure",
    )
    server.start()
    wait_for_logs(server, "start_node_query")

    return DatastoreDBNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(26257)
    )


@pytest.fixture(scope="module")
def old_ssl_cockroach(request):
    server = DockerContainer(
        image="mcuoorb/insecurecockroach:latest",
        ports=[26257],
        command="start-single-node",
    )
    server.start()
    wait_for_logs(server, "start_node_query")

    return DatastoreDBNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(26257)
    )


@pytest.fixture(scope="module")
def good_yugabyte(request):
    server = DockerContainer(
        image="yugabytedb/yugabyte:2.25.2.0-b359",
        ports=[5433],
        command='bash -c "bin/yugabyted cert generate_server_certs --base_dir /yugabyte/certs --hostnames `hostname`  && bin/yugabyted start --secure --certs_dir=/yugabyte/certs/generated_certs/`hostname` --advertise_address=`hostname` --background=false"',
    )
    server.start()
    wait_for_logs(server, "Data placement constraint successfully verified")

    return DatastoreDBNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(5433)
    )


@pytest.fixture(scope="module")
def no_ssl_yugabyte(request):
    server = DockerContainer(
        image="yugabytedb/yugabyte:2.25.2.0-b359",
        ports=[5433],
        command="bin/yugabyted start --background=false",
    )
    server.start()
    wait_for_logs(server, "Data placement constraint successfully verified")

    return DatastoreDBNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(5433)
    )


@pytest.fixture(scope="module")
def old_ssl_yugabyte(request):
    import base64

    config = '{"tserver_flags": "ysql_pg_conf_csv=\\"ssl_min_protocol_version=\'TLSv1.1\'\\""}'
    config = base64.b64encode(config.encode("utf-8"))  # Avoid escaping hell

    server = DockerContainer(
        image="yugabytedb/yugabyte:2.25.2.0-b359",
        ports=[5433],
        command=f'bash -c "echo {config.decode("utf-8")} | base64 -d > /conf.conf && cat /conf.conf && bin/yugabyted cert generate_server_certs --base_dir /yugabyte/certs --hostnames `hostname` && bin/yugabyted start --secure --certs_dir=/yugabyte/certs/generated_certs/`hostname` --advertise_address=`hostname` --background=false --conf /conf.conf"',
    )
    server.start()
    wait_for_logs(server, "Data placement constraint successfully verified")

    return DatastoreDBNode(
        "test", server.get_container_host_ip(), server.get_exposed_port(5433)
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


def test_datastoredbmode_connect_old_ssl_yugabyte(old_ssl_yugabyte):
    is_reachable, _ = old_ssl_yugabyte.is_reachable()
    assert is_reachable


def test_datastoredbmode_secure_mode_good_cockroach(good_cockroach):
    is_secure, _ = good_cockroach.runs_in_secure_mode()
    assert is_secure


def test_datastoredbmode_secure_mode_good_yugabyte(good_yugabyte):
    is_secure, _ = good_yugabyte.runs_in_secure_mode()
    assert is_secure


def test_datastoredbmode_secure_mode_no_ssl_cockroach(no_ssl_cockroach):
    is_secure, _ = no_ssl_cockroach.runs_in_secure_mode()
    assert not is_secure


def test_datastoredbmode_secure_mode_no_ssl_yugabyte(no_ssl_yugabyte):
    is_secure, _ = no_ssl_yugabyte.runs_in_secure_mode()
    assert not is_secure


def test_datastoredbmode_secure_mode_old_ssl_cockroach(old_ssl_cockroach):
    is_secure, _ = old_ssl_cockroach.runs_in_secure_mode()
    assert is_secure


def test_datastoredbmode_secure_mode_old_ssl_yugabyte(old_ssl_yugabyte):
    is_secure, _ = old_ssl_yugabyte.runs_in_secure_mode()
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


def test_datastoredbmode_reject_legacy_old_ssl_yugabyte(old_ssl_yugabyte):
    legacy_rejected, _ = old_ssl_yugabyte.legacy_ssl_version_rejected()
    assert not legacy_rejected
