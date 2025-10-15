import yaml
from implicitdict import StringBasedDateTime
from yaml.representer import Representer

from monitoring.mock_uss.app import webapp
from monitoring.mock_uss.config import KEY_AUTH_SPEC, KEY_DSS_URL
from monitoring.mock_uss.tracer.config import (
    KEY_TRACER_KML_FOLDER,
    KEY_TRACER_KML_SERVER,
    KEY_TRACER_OUTPUT_FOLDER,
)
from monitoring.mock_uss.tracer.observation_areas import ObservationAreaID
from monitoring.mock_uss.tracer.tracerlog import DummyLogger, Logger
from monitoring.monitorlib import infrastructure
from monitoring.monitorlib.auth import make_auth_adapter
from monitoring.monitorlib.fetch import scd
from monitoring.monitorlib.infrastructure import AuthAdapter, AuthSpec, UTMClientSession
from monitoring.monitorlib.rid import RIDVersion

yaml.add_representer(StringBasedDateTime, Representer.represent_str)


scd_cache: dict[ObservationAreaID, dict[str, scd.FetchedEntity]] = {}


def _get_tracer_logger() -> Logger:
    kml_server = webapp.config[KEY_TRACER_KML_SERVER]
    kml_folder = webapp.config[KEY_TRACER_KML_FOLDER]
    output_folder = webapp.config[KEY_TRACER_OUTPUT_FOLDER]
    if kml_server and not kml_folder:
        raise ValueError(
            f"If {KEY_TRACER_KML_SERVER} is specified, {KEY_TRACER_KML_FOLDER} must also be specified"
        )
    kml_session = (
        infrastructure.KMLGenerationSession(kml_server, kml_folder)
        if kml_server
        else None
    )
    return Logger(output_folder, kml_session) if output_folder else DummyLogger()


tracer_logger: Logger = _get_tracer_logger()


_adapters: dict[AuthSpec, AuthAdapter] = {}


def resolve_auth_spec(requested_auth_spec: AuthSpec | None) -> AuthSpec:
    if not requested_auth_spec:
        if KEY_AUTH_SPEC not in webapp.config or not webapp.config[KEY_AUTH_SPEC]:
            raise ValueError(
                "Auth spec was not specified explicitly nor mock_uss configuration"
            )
        else:
            return webapp.config[KEY_AUTH_SPEC]
    else:
        return requested_auth_spec


def resolve_rid_dss_base_url(dss_base_url: str | None, rid_version: RIDVersion) -> str:
    if not dss_base_url:
        dss_base_url = webapp.config.get(KEY_DSS_URL)

        if not dss_base_url:
            raise ValueError(
                "DSS base URL was not specified explicitly nor in mock_uss_configuration"
            )

    if rid_version == RIDVersion.f3411_19:
        return dss_base_url
    elif rid_version == RIDVersion.f3411_22a:
        return dss_base_url + "/rid/v2"
    else:
        raise NotImplementedError(
            f"Cannot resolve DSS URL for RID version {rid_version}"
        )


def resolve_scd_dss_base_url(dss_base_url: str | None) -> str:
    if not dss_base_url:
        dss_base_url = webapp.config.get(KEY_DSS_URL)

        if not dss_base_url:
            raise ValueError(
                "DSS base URL was not specified explicitly nor in mock_uss_configuration"
            )

    return dss_base_url


def get_client(auth_spec: AuthSpec, dss_base_url: str) -> UTMClientSession:
    if auth_spec not in _adapters:
        _adapters[auth_spec] = make_auth_adapter(auth_spec)
    return UTMClientSession(dss_base_url, _adapters[auth_spec])
