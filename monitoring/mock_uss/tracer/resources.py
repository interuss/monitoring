import argparse
import datetime
import shlex

import s2sphere

from monitoring import mock_uss
from monitoring.monitorlib import auth, infrastructure, geo
from monitoring.mock_uss import webapp, tracer
import monitoring.mock_uss.tracer.config
from monitoring.mock_uss.tracer import tracerlog


def get_options():
    parser = argparse.ArgumentParser(
        description="Subscribe to changes in DSS-tracked Entity status"
    )
    ResourceSet.add_arguments(parser)
    tracer_options = webapp.config[tracer.config.KEY_TRACER_OPTIONS]
    return parser.parse_args(shlex.split(tracer_options))


class ResourceSet(object):
    """Set of resources necessary to obtain information from the UTM system."""

    def __init__(
        self,
        dss_client: infrastructure.UTMClientSession,
        area: s2sphere.LatLngRect,
        logger: tracerlog.Logger,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
    ):
        self.dss_client = dss_client
        self.area = area
        self.logger = logger
        self.start_time = start_time
        self.end_time = end_time

        self.scd_cache = {}

    @classmethod
    def add_arguments(cls, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--area",
            required=True,
            help="`lat,lng,lat,lng` for box containing the area to trace interactions for",
        )
        parser.add_argument(
            "--start-time",
            default=datetime.datetime.utcnow().isoformat(),
            help="ISO8601 UTC datetime at which to start polling",
        )
        parser.add_argument(
            "--trace-hours", type=float, default=18, help="Number of hours to trace for"
        )
        parser.add_argument(
            "--output-folder", help="Path of folder in which to write logs"
        )
        parser.add_argument(
            "--kml-server",
            help="Base URL of KML-generating server",
            type=str,
            default=None,
        )
        parser.add_argument(
            "--kml-folder", help="Name of path on KML server", type=str, default=None
        )
        parser.add_argument(
            "--rid-isa-poll-interval",
            type=float,
            default=0,
            help="Seconds beteween each poll of the DSS for ISAs, 0 to disable DSS polling for ISAs",
        )
        parser.add_argument(
            "--scd-operation-poll-interval",
            type=float,
            default=0,
            help="Seconds between each poll of the DSS for Operations, 0 to disable DSS polling for Operations",
        )
        parser.add_argument(
            "--scd-constraint-poll-interval",
            type=float,
            default=0,
            help="Seconds between each poll of the DSS for Constraints, 0 to disable DSS polling for Constraints",
        )
        parser.add_argument(
            "--monitor-rid",
            action="store_true",
            default=False,
            help="If specified, monitor ISA activity per the remote ID standard",
        )
        parser.add_argument(
            "--monitor-scd",
            action="store_true",
            default=False,
            help="If specified, monitor Operation and Constraint activity per the strategic deconfliction standard",
        )

    @classmethod
    def from_arguments(cls, args: argparse.Namespace):
        adapter: auth.AuthAdapter = auth.make_auth_adapter(
            webapp.config[mock_uss.config.KEY_AUTH_SPEC]
        )
        dss_client = infrastructure.UTMClientSession(
            webapp.config[mock_uss.config.KEY_DSS_URL], adapter
        )
        area: s2sphere.LatLngRect = geo.make_latlng_rect(args.area)
        start_time = datetime.datetime.fromisoformat(args.start_time)
        end_time = start_time + datetime.timedelta(hours=args.trace_hours)
        if args.kml_server and args.kml_folder is None:
            raise ValueError(
                "If --kml-server is specified, --kml-folder must also be specified"
            )
        kml_session = (
            infrastructure.KMLGenerationSession(args.kml_server, args.kml_folder)
            if args.kml_server
            else None
        )
        logger = (
            tracerlog.Logger(args.output_folder, kml_session)
            if args.output_folder
            else None
        )
        return ResourceSet(dss_client, area, logger, start_time, end_time)
