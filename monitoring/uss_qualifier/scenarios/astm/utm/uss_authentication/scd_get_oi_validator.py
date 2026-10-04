from uas_standards.astm.f3548.v21.api import (
    OPERATIONS,
    OperationID,
)

from monitoring.monitorlib.fetch import QueryType
from monitoring.uss_qualifier.resources.astm.f3548.v21.uss import USSInstance
from monitoring.uss_qualifier.scenarios.astm.utm.auth_validator import (
    GenericAuthValidator,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario


class GetOperationalIntentAuthValidator:
    def __init__(
        self,
        scenario: TestScenario,
        generic_validator: GenericAuthValidator,
        uss: USSInstance,
        op_intent_id: str,
    ):
        self._scenario = scenario
        self._generic_validator = generic_validator
        self._pid = uss.participant_id
        op = OPERATIONS[OperationID.GetOperationalIntentDetails]
        self._query_kwargs = dict(
            verb=op.verb,
            url=op.path.format(entityid=op_intent_id),
            query_type=QueryType.F3548v21USSGetOperationalIntentDetails,
            participant_id=self._pid,
        )

    def verify_endpoints_authentication(self):
        self._verify_missing_credentials()

    def _verify_missing_credentials(self):
        query = self._generic_validator.query_no_auth(**self._query_kwargs)
        with self._scenario.check(
            "Get operational intent details with missing credentials",
            self._pid,
        ) as check:
            if query.status_code != 401:
                check.record_failed(
                    summary=f"Expected 401, got {query.status_code}",
                    details=str(query.failure_details),
                    query_timestamps=[query.request.timestamp],
                )

        self._generic_validator.verify_4xx_response(query)
