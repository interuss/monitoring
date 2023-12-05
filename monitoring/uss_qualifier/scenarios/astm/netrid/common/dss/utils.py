from typing import Optional

from monitoring.monitorlib.fetch import rid as fetch
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.monitorlib.mutate import rid as mutate
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.scenarios.scenario import (
    GenericTestScenario,
)


def delete_isa_if_exists(
    scenario: GenericTestScenario,
    isa_id: str,
    rid_version: RIDVersion,
    session: UTMClientSession,
    participant_id: Optional[str] = None,
    ignore_base_url: Optional[str] = None,
):
    """
    Deletes an ISA from the DSS that lives behind the provided session, and takes
    care of notifying subscribers if any exists.

    Args:
        scenario: scenario for generating the required checks and recording queries
        isa_id: ISA to delete
        rid_version: RID version to use
        session: the connection to the DSS
        participant_id: the participant ID of the DSS, if it is known
        ignore_base_url: the base URL provided by the uss_qualifier to filter out notifications
            that are sent to itself

    """
    fetched = fetch.isa(
        isa_id,
        rid_version=rid_version,
        session=session,
        participant_id=participant_id,
    )
    scenario.record_query(fetched.query)
    with scenario.check("Successful ISA query", [participant_id]) as check:
        if not fetched.success and fetched.status_code != 404:
            check.record_failed(
                "ISA information could not be retrieved",
                Severity.High,
                f"{participant_id} DSS instance returned {fetched.status_code} when queried for ISA {isa_id}",
                query_timestamps=[fetched.query.request.timestamp],
            )

    if fetched.success:
        deleted = mutate.delete_isa(
            isa_id,
            fetched.isa.version,
            rid_version,
            session,
            participant_id=participant_id,
        )
        scenario.record_query(deleted.dss_query.query)
        for subscriber_id, notification in deleted.notifications.items():
            scenario.record_query(notification.query)
        with scenario.check("Removed pre-existing ISA", [participant_id]) as check:
            if not deleted.dss_query.success:
                check.record_failed(
                    "Could not delete pre-existing ISA",
                    Severity.High,
                    f"Attempting to delete ISA {isa_id} from the {participant_id} DSS returned error {deleted.dss_query.status_code}",
                    query_timestamps=[deleted.dss_query.query.request.timestamp],
                )

        for subscriber_url, notification in deleted.notifications.items():
            # If a base URL to be ignored is specified, skip the check:
            # This is useful to ignore notifications we send to ourselves
            # and that are likely failures as we don't have the machinery to accept them.
            if ignore_base_url is None or ignore_base_url not in subscriber_url:
                pid = (
                    notification.query.participant_id
                    if "participant_id" in notification.query
                    else None
                )
                with scenario.check(
                    "Notified subscriber", [pid] if pid else []
                ) as check:
                    if not notification.success:
                        check.record_failed(
                            "Could not notify ISA subscriber",
                            Severity.Medium,
                            f"Attempting to notify subscriber for ISA {isa_id} at {subscriber_url} resulted in {notification.status_code}",
                            query_timestamps=[notification.query.request.timestamp],
                        )
