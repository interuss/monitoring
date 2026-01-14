from datetime import datetime

import pytest
from implicitdict import StringBasedDateTime

from monitoring.monitorlib.fetch import (
    Query,
    RequestDescription,
    ResponseDescription,
)
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.uss_qualifier.configurations.configuration import ParticipantID

from .client_interuss import InterUSSVersioningClient, VersionQueryError


@pytest.fixture
def client():
    return InterUSSVersioningClient(UTMClientSession(prefix_url="/"), ParticipantID())


def build_query_response(code, data):
    return Query(
        request=RequestDescription(
            method=None,
            url=None,
            initiated_at=StringBasedDateTime(datetime.fromtimestamp(0)),
        ),
        response=ResponseDescription(elapsed_s=0, reported=None, code=code, json=data),
    )


def test_get_version_nominal(mocker, client):
    mocker.patch(
        "monitoring.monitorlib.clients.versioning.client_interuss.query_and_describe",
        return_value=build_query_response(
            200, {"system_identity": "test", "system_version": "test_version"}
        ),
    )

    assert client.get_version("test").version == "test_version"


def test_get_version_non_200(mocker, client):
    mocker.patch(
        "monitoring.monitorlib.clients.versioning.client_interuss.query_and_describe",
        return_value=build_query_response(
            500, {"system_identity": "test", "system_version": "test_version"}
        ),
    )

    with pytest.raises(VersionQueryError, match="rather than 200 as expected"):
        client.get_version("test")


def test_get_version_wrong_body(mocker, client):
    mocker.patch(
        "monitoring.monitorlib.clients.versioning.client_interuss.query_and_describe",
        return_value=build_query_response(200, None),
    )

    with pytest.raises(
        VersionQueryError, match="Response to get version could not be parsed"
    ):
        client.get_version("test")


def test_get_version_no_system_identity(mocker, client):
    mocker.patch(
        "monitoring.monitorlib.clients.versioning.client_interuss.query_and_describe",
        return_value=build_query_response(200, {"system_version": "test_version"}),
    )

    with pytest.raises(
        VersionQueryError,
        match="Response to get version didn't return a system identity",
    ):
        client.get_version("test")


def test_get_version_no_system_version(mocker, client):
    mocker.patch(
        "monitoring.monitorlib.clients.versioning.client_interuss.query_and_describe",
        return_value=build_query_response(200, {"system_identity": "test"}),
    )

    with pytest.raises(
        VersionQueryError,
        match="Response to get version didn't return a system version",
    ):
        client.get_version("test")


def test_get_version_another_identity(mocker, client):
    mocker.patch(
        "monitoring.monitorlib.clients.versioning.client_interuss.query_and_describe",
        return_value=build_query_response(
            200, {"system_identity": "test2", "system_version": "test_version"}
        ),
    )

    with pytest.raises(
        VersionQueryError,
        match="Response to get version indicated version for system 'test2'",
    ):
        client.get_version("test")
