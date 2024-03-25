from typing import List

from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstance
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from uas_standards.astm.f3548.v21.api import OperationalIntentReference


def validate_clear_area(
    scenario: TestScenario,
    dss: DSSInstance,
    areas: List[Volume4D],
    ignore_self: bool,
) -> List[OperationalIntentReference]:
    found_intents = []
    for area in areas:
        with scenario.check("DSS responses", [dss.participant_id]) as check:
            try:
                op_intents, query = dss.find_op_intent(area.to_f3548v21())
                scenario.record_query(query)
            except QueryError as e:
                scenario.record_queries(e.queries)
                query = e.queries[0]
                check.record_failed(
                    summary="Error querying DSS for operational intents",
                    details=f"See query; {e}",
                    query_timestamps=[query.request.timestamp],
                )
        found_intents.extend(op_intents)

        with scenario.check("Area is clear of op intents") as check:
            if ignore_self:
                uss_qualifier_sub = dss.client.auth_adapter.get_sub()
                op_intents = [
                    oi for oi in op_intents if oi.manager != uss_qualifier_sub
                ]
            if op_intents:
                summary = f"{len(op_intents)} operational intent{'s' if len(op_intents) > 1 else ''} found in test area"
                details = (
                    "The following operational intents were observed even though the area was expected to be clear:\n"
                    + "\n".join(
                        f"* {oi.id} managed by {oi.manager}" for oi in op_intents
                    )
                )
                check.record_failed(
                    summary=summary,
                    details=details,
                    query_timestamps=[query.request.timestamp],
                )

    return found_intents
