from typing import Optional

from monitoring.monitorlib.fetch import rid as fetch
from monitoring.monitorlib.mutate import rid as mutate
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario


def delete_isa_if_exists(
    scenario: GenericTestScenario,
    isa_id: str,
    rid_version: RIDVersion,
    session: UTMClientSession,
    participant_id: Optional[str] = None,
):
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
            with scenario.check("Notified subscriber", [subscriber_url]) as check:
                # TODO: Find a better way to identify a subscriber who couldn't be notified
                if not notification.success:
                    check.record_failed(
                        "Could not notify ISA subscriber",
                        Severity.Medium,
                        f"Attempting to notify subscriber for ISA {isa_id} at {subscriber_url} resulted in {notification.status_code}",
                        query_timestamps=[notification.query.request.timestamp],
                    )
