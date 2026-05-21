from collections.abc import Callable, Iterable
from numbers import Number
from types import NoneType
from typing import Any

import arrow
import bc_jsonpath_ng
from implicitdict import StringBasedDateTime

from monitoring.monitorlib.clients.flight_planning.flight_info import FlightInfo
from monitoring.monitorlib.dicts import JSONAddress, JSONPath
from monitoring.uss_qualifier.scenarios.scenario import PendingCheck

CompatibilityEvaluator = Callable[[Any, Any, JSONAddress, PendingCheck], None]
"""Evaluates whether an as-planned value is compatible with an as-requested value.
    Arguments:
        * as_requested: The value, as requested.
        * as_planned: The value, as planned.
        * address: Location of the value within the content structure being evalated.
        * check: Pending check for whether the planned value is compatible with the requested value.
"""


def values_exactly_equal(
    as_requested: str | Number | StringBasedDateTime | None,
    as_planned: str | Number | StringBasedDateTime | None,
    address: JSONAddress,
    check: PendingCheck,
):
    """Implements CompatibilityEvaluator pattern, requiring requested and planned values to match exactly."""

    for dtype in (StringBasedDateTime, Number, str, NoneType):
        if isinstance(as_requested, dtype):
            if not isinstance(as_planned, dtype):
                check.record_failed(
                    summary=f"Mismatched data type in {address}",
                    details=f"The data type in {address} was a {dtype.__name__} in the request, but {type(as_planned).__name__} ('{as_planned}') as planned",
                )
                return
            if dtype == StringBasedDateTime:
                assert isinstance(as_planned, StringBasedDateTime)
                assert isinstance(as_requested, StringBasedDateTime)
                equal = as_planned.datetime == as_requested.datetime
            else:
                equal = as_planned == as_requested
            if not equal:
                check.record_failed(
                    summary=f"Incompatible flight info at {address}",
                    details=f"The value at {address} as requested was '{as_requested}', but as planned was '{as_planned}' when exact equality was expected",
                )
            return

    raise NotImplementedError(
        f"Means to compare data type {type(as_requested).__name__} (in field {address}) for equality has not yet been implemented"
    )


def times_not_later_than_specified_or_now(
    as_requested: StringBasedDateTime,
    as_planned: StringBasedDateTime,
    address: JSONAddress,
    check: PendingCheck,
):
    """Implements CompatibilityEvaluator pattern for StringBasedDateTimes, requiring planned value to not be later than
    requested or now, which ever is later.  This allows a client to plan a time to be the current wall time when the
    requested time was earlier than the wall time."""

    if not isinstance(as_requested, StringBasedDateTime):
        check.record_failed(
            summary=f"Incorrect requested data type in {address}",
            details=f"Expected a StringBasedDateTime in {address}, but found a {type(as_requested).__name__} ('{as_requested}') in the request instead",
        )
        return
    if not isinstance(as_planned, StringBasedDateTime):
        check.record_failed(
            summary=f"Incorrect data type in {address}",
            details=f"Expected a StringBasedDateTime in {address}, but found a {type(as_planned).__name__} ('{as_planned}') as planned instead",
        )
        return
    now = arrow.utcnow().datetime
    latest = now if as_requested.datetime < now else as_requested.datetime
    if as_planned.datetime > latest:
        check.record_failed(
            f"Planned time {as_planned} is too late",
            details=f"Requested time no later than {as_requested} (or now, at {now}) for {address}, but planned time was {as_planned} which is later than the latest time allowed of {latest}",
        )


def _resolve_addresses(
    paths: Iterable[JSONPath] | JSONPath, content: dict[str, Any]
) -> Iterable[JSONAddress]:
    if isinstance(paths, JSONPath):
        paths = [paths]
    for path in paths:
        for match in bc_jsonpath_ng.parser.parse(path).find(content):
            full_path = "$." + str(match.full_path)
            full_path = full_path.replace(".[", "[")
            yield JSONAddress(full_path)


def _require_compatible_values(
    as_requested: dict | list | Any,
    as_planned: dict | list | Any,
    check: PendingCheck,
    default_compatibility: CompatibilityEvaluator | None,
    compatibility: dict[JSONAddress, CompatibilityEvaluator | None] | None,
    address: JSONAddress = JSONAddress("$"),
):
    # Use an explicit evaluator for this value if there is one
    if compatibility and address in compatibility:
        evaluator = compatibility[address]
        if evaluator is not None:
            evaluator(as_requested, as_planned, address, check)

    elif isinstance(as_requested, dict):
        if not isinstance(as_planned, dict):
            check.record_failed(
                summary=f"Mismatched data in {address}",
                details=f"The data type in {address} was an object/dictionary in the request, but '{as_planned}' ({type(as_planned)}) indicated as planned",
            )
            return
        for k, v in as_requested.items():
            if k in as_planned:
                _require_compatible_values(
                    v,
                    as_planned[k],
                    check,
                    default_compatibility,
                    compatibility,
                    address + "." + k,
                )
            else:
                check.record_failed(
                    summary=f"As-planned missing {address}.{k}",
                    details=f"The request specified {address}.{k} as '{v}' but there was no such '{k}' key in {address} as planned",
                )
                return

    elif isinstance(as_requested, list) and not isinstance(as_requested, str):
        if not isinstance(as_planned, list):
            check.record_failed(
                summary=f"Mismatched data in {address}",
                details=f"The data type in {address} was a list in the request, but '{as_planned}' ({type(as_planned)}) indicated as planned",
            )
            return
        if len(as_requested) != len(as_planned):
            check.record_failed(
                summary=f"Mismatched list at {address}",
                details=f"As requested, {address} has {len(as_requested)} elements, but as planned, {address} has {len(as_planned)} elements (equality expected)",
            )
            return
        for i, v in enumerate(as_requested):
            _require_compatible_values(
                v,
                as_planned[i],
                check,
                default_compatibility,
                compatibility,
                address + f"[{i}]",
            )

    else:
        if default_compatibility:
            default_compatibility(as_requested, as_planned, address, check)
        else:
            raise NotImplementedError(
                f"Means to compare data type {type(as_requested)} in as_planned field {address} has not yet been implemented"
            )


def require_compatible_values(
    as_requested: FlightInfo,
    as_planned: FlightInfo,
    check: PendingCheck,
    compatibility: dict[JSONPath, CompatibilityEvaluator | None] | None = None,
    default_compatibility: CompatibilityEvaluator | None = None,
) -> None:
    """Requires values in as_planned FlightInfo to be compatible with those in as_requested.

    Arguments:
        * as_requested: The flight information that was requested.
        * as_planned: The flight information that was actually planned.
        * check: Pending check that should fail if any planned values are incompatible with the request.
        * default_compatibility: If specified, determine if a particular value pair is compatible using this method when
            no other method is specified via `compatibility`
        * compatibility: If specified, mapping between JSONPaths (e.g., $.basic_information.area[0].time_start)
            describing element(s) of as_requested and the method to determine compatibility between each matching value
            pair.
    """
    compatibility_by_address = dict()
    if compatibility:
        for json_path, evaluator in compatibility.items():
            for address in _resolve_addresses(json_path, as_requested):
                compatibility_by_address[address] = evaluator
    _require_compatible_values(
        as_requested, as_planned, check, default_compatibility, compatibility_by_address
    )
