import datetime

from loguru import logger
from uas_standards.astm.f3548.v21.api import ExchangeRecord, USSLogSet

from monitoring.mock_uss.tracer.log_types import (
    BadRoute,
    ConstraintNotification,
    ObservationAreaImportError,
    OperationalIntentNotification,
    PollConstraints,
    PollFlights,
    PollISAs,
    PollOperationalIntents,
    PollStart,
    RIDISANotification,
    RIDSubscribe,
    RIDUnsubscribe,
    SCDSubscribe,
    SCDUnsubscribe,
    TracerLogEntry,
    TracerShutdown,
)
from monitoring.mock_uss.tracer.tracerlog import load_logs
from monitoring.monitorlib.scd import (
    make_exchange_record,
    make_request_exchange_record,
)

_F3548_LOG_TYPES: set[type[TracerLogEntry]] = {
    SCDSubscribe,
    SCDUnsubscribe,
    PollOperationalIntents,
    PollConstraints,
    OperationalIntentNotification,
    ConstraintNotification,
}

_NON_F3548_LOG_TYPES: set[type[TracerLogEntry]] = {
    PollStart,
    RIDSubscribe,
    RIDISANotification,
    RIDUnsubscribe,
    PollISAs,
    PollFlights,
    BadRoute,
    ObservationAreaImportError,
    TracerShutdown,
}


def extract_exchange_records(
    log_entry: TracerLogEntry,
    seen_uss_queries: set[tuple[str, datetime.datetime]] | None = None,
    include_headers: set[str] | None = None,
) -> list[ExchangeRecord]:
    """Extract ASTM F3548-21 ExchangeRecords from a TracerLogEntry."""
    if isinstance(log_entry, SCDSubscribe):
        return [
            make_exchange_record(
                log_entry.changed_subscription, include_headers=include_headers
            )
        ]
    elif isinstance(log_entry, SCDUnsubscribe):
        records = [
            make_exchange_record(
                log_entry.existing_subscription, include_headers=include_headers
            )
        ]
        if (
            "deleted_subscription" in log_entry
            and log_entry.deleted_subscription is not None
        ):
            records.append(
                make_exchange_record(
                    log_entry.deleted_subscription, include_headers=include_headers
                )
            )
        return records
    elif isinstance(log_entry, (PollOperationalIntents, PollConstraints)):
        records = [
            make_exchange_record(
                log_entry.poll.dss_query, include_headers=include_headers
            )
        ]
        uss_queries = list(log_entry.poll.uss_queries.values()) + list(
            log_entry.poll.cached_uss_queries.values()
        )
        for q in uss_queries:
            if seen_uss_queries is not None:
                key = (q.request.url, q.request.timestamp)
                if key in seen_uss_queries:
                    continue
                seen_uss_queries.add(key)
            records.append(make_exchange_record(q, include_headers=include_headers))
        return records
    elif isinstance(log_entry, (OperationalIntentNotification, ConstraintNotification)):
        return [
            make_request_exchange_record(
                log_entry.request, include_headers=include_headers
            )
        ]
    elif isinstance(log_entry, tuple(_NON_F3548_LOG_TYPES)):
        return []
    else:
        raise NotImplementedError(
            f"Cannot extract ExchangeRecords from {type(log_entry).__name__}"
        )


def make_usslogset(
    log_folder: str, include_headers: set[str] | None = None
) -> USSLogSet:
    """Generate an ASTM F3548-21 USSLogSet from a folder of tracer log files."""
    messages: list[ExchangeRecord] = []
    seen_uss_queries: set[tuple[str, datetime.datetime]] = set()
    for filename, log_entry in load_logs(
        log_folder,
        acceptable_types=_F3548_LOG_TYPES,
        ignored_types=_NON_F3548_LOG_TYPES,
    ):
        try:
            messages.extend(
                extract_exchange_records(
                    log_entry,
                    seen_uss_queries=seen_uss_queries,
                    include_headers=include_headers,
                )
            )
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"Skipping {filename} because of invalid data: {e}")
            continue

    return USSLogSet(messages=messages)
