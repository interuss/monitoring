from typing import Optional

from implicitdict import ImplicitDict
from loguru import logger

from monitoring.monitorlib.fetch import settings
from monitoring.uss_qualifier.resources.resource import Resource


class QueryBehaviorSpecification(ImplicitDict):
    connect_timeout_seconds: Optional[float]
    """Number of seconds to allow for establishing a connection.  Use 0 for no timeout."""

    read_timeout_seconds: Optional[float]
    """Number of seconds to allow for a request to complete after establishing a connection.  Use 0 for no timeout."""

    attempts: Optional[int]
    """Number of attempts to query when experiencing a retryable error like a timeout"""

    add_request_id: Optional[bool]
    """Whether to automatically add a `request_id` field to any request with a JSON body and no pre-existing `request_id` field"""


class QueryBehaviorResource(Resource[QueryBehaviorSpecification]):
    """When declared, this resource adjusts the settings for all queries made by uss_qualifier.

    This resource is not intended to be used in any test scenario; instead, its mutating actions are performed as soon
    as it is created (at the beginning of the test run).
    """

    def __init__(
        self,
        specification: QueryBehaviorSpecification,
        resource_origin: str,
    ):
        super(QueryBehaviorResource, self).__init__(specification, resource_origin)

        if (
            "connect_timeout_seconds" in specification
            and specification.connect_timeout_seconds is not None
        ):
            if specification.connect_timeout_seconds < 0:
                raise ValueError("A negative connection timeout does not make sense")
            if specification.connect_timeout_seconds == 0:
                settings.connect_timeout_seconds = None
            else:
                settings.connect_timeout_seconds = specification.connect_timeout_seconds
            logger.info(
                f"QueryBehaviorResource: Fetch query connect timeout set to {settings.connect_timeout_seconds} seconds"
            )

        if (
            "read_timeout_seconds" in specification
            and specification.read_timeout_seconds is not None
        ):
            if specification.read_timeout_seconds < 0:
                raise ValueError("A negative read timeout does not make sense")
            if specification.read_timeout_seconds == 0:
                settings.read_timeout_seconds = None
            else:
                settings.read_timeout_seconds = specification.read_timeout_seconds
            logger.info(
                f"QueryBehaviorResource: Fetch query read timeout set to {settings.read_timeout_seconds} seconds"
            )

        if "attempts" in specification and specification.attempts is not None:
            if specification.attempts < 1:
                raise ValueError(
                    "It only makes sense to make at least one query attempt"
                )
            settings.attempts = specification.attempts
            logger.info(
                f"QueryBehaviorResource: Fetch query number of attempts set to {settings.attempts}"
            )

        if (
            "add_request_id" in specification
            and specification.add_request_id is not None
        ):
            settings.add_request_id = specification.add_request_id
            logger.info(
                f"QueryBehaviorResource: Fetch query set to {'' if settings.add_request_id else 'not '} add `request_id`"
            )
