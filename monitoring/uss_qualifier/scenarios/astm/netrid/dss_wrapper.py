import datetime
from typing import Optional, List, Set, Dict, Any

import s2sphere
from implicitdict import StringBasedDateTime

from monitoring.monitorlib import schema_validation
from monitoring.monitorlib.fetch import (
    QueryError,
    Query,
    RequestDescription,
    ResponseDescription,
)
from monitoring.monitorlib.fetch import rid as fetch
from monitoring.monitorlib.fetch.rid import (
    FetchedSubscription,
    FetchedSubscriptions,
    RIDQuery,
    FetchedISA,
    FetchedISAs,
)
from monitoring.monitorlib.mutate import rid as mutate
from monitoring.monitorlib.mutate.rid import ISAChange, ChangedSubscription
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstance
from monitoring.uss_qualifier.scenarios.astm.netrid.common.dss.isa_validator import (
    ISAValidator,
)
from monitoring.uss_qualifier.scenarios.scenario import (
    PendingCheck,
    TestScenario,
)

MAX_SKEW = 1e-6  # seconds maximum difference between expected and actual timestamps


class DSSWrapper(object):
    """Wraps a DSS instance with test checks."""

    # TODO: adapt other functions with corresponding test step and sub-checks like it is done for put_isa

    _scenario: TestScenario
    _dss: DSSInstance

    def __init__(
        self,
        scenario: TestScenario,
        dss: DSSInstance,
    ):
        self._scenario = scenario
        self._dss = dss

    @property
    def participant_id(self) -> str:
        return self._dss.participant_id

    @property
    def base_url(self) -> str:
        return self._dss.base_url

    @property
    def has_private_address(self) -> bool:
        return self._dss.has_private_address

    # TODO: QueryError is not actually raised for RID functions, this function and its uses should be removed
    def _handle_query_error(
        self,
        check: PendingCheck,
        e: QueryError,
    ):
        for q in e.queries:
            self._scenario.record_query(q)
        check.record_failed(
            summary=f"Error when querying DSS",
            severity=Severity.High,
            details=f"{str(e)}\n\nStack trace:\n{e.stacktrace}",
            query_timestamps=[q.request.timestamp for q in e.queries],
        )

    def handle_query_result(
        self,
        check: PendingCheck,
        q: RIDQuery,
        fail_msg: str,
        required_status_code: Optional[Set[int]] = None,
        severity: Severity = Severity.High,
        fail_details: Optional[str] = None,
    ):
        """
        Handle the result of the query, based on the expected result codes versus the actual one,
        and fail the specified check accordingly if the query's HTTP response code is not a success or, if specified,
        it is not present in `required_status_code`.

        Note that this won't check anything about the response payloads: this is left to the discretion of the caller.

        The passed query will be properly recorded in the scenario and in case of check failure, its timestamp will
        be associated with the check.

        Additionally, upon failure, the participant_id of the underlying DSS is set as the check's participants.

        :param check: the check to fail if q is not successful (or, when applicable, its response code is not in required_status_code)
        :param q: the query to check
        :param fail_msg: the message to use when failing the check
        :param required_status_code: the set of status codes that are considered successful. If this is None then success is defined by `q.success`
        :param severity: the severity of the check failure
        :param fail_details: the details passed to check.record_fail
        """
        self._scenario.record_query(q.query)
        if (required_status_code is None and not q.success) or (
            required_status_code is not None
            and q.status_code not in required_status_code
        ):
            check.record_failed(
                summary=fail_msg,
                severity=severity,
                details=f"{fail_details}\n{q.status_code} response: "
                + "\n".join(q.errors)
                if fail_details is not None
                else f"{q.status_code} response: " + "\n".join(q.errors),
                query_timestamps=[q.query.request.timestamp],
            )

    def search_isas(
        self,
        main_check: PendingCheck,
        area: List[s2sphere.LatLng],
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
    ) -> FetchedISAs:
        """Search for ISAs at the DSS.

        Query failure will fail the provided main check. If the query is successful, the sub-checks of the test step
        described in '[v19|v22a]/dss/test_steps/search_isas.md' are performed. Some of those might fail the main check.

        :return: the DSS response
        """

        isas = fetch.isas(
            area=area,
            start_time=start_time,
            end_time=end_time,
            rid_version=self._dss.rid_version,
            session=self._dss.client,
            participant_id=self._dss.participant_id,
        )
        self.handle_query_result(
            main_check,
            isas,
            f"Failed to search ISAs in {area} from {start_time} to {end_time}",
        )

        dss_id = [self._dss.participant_id]
        t_dss = isas.query.request.timestamp

        with self._scenario.check("ISAs search response format", dss_id) as sub_check:
            errors = schema_validation.validate(
                self._dss.rid_version.openapi_path,
                self._dss.rid_version.openapi_search_isas_response_path,
                isas.query.response.json,
            )
            if errors:
                details = "\n".join(f"[{e.json_path}] {e.message}" for e in errors)
                sub_check.record_failed(
                    "Search ISA response format was invalid",
                    Severity.Medium,
                    "Found the following schema validation errors in the DSS response:\n"
                    + details,
                    query_timestamps=[t_dss],
                )

        return isas

    def search_isas_expect_response_code(
        self,
        main_check: PendingCheck,
        expected_error_codes: Set[int],
        area: List[s2sphere.LatLng],
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
    ) -> FetchedISAs:
        """Attempt to search for ISAs at the DSS, and expect the specified HTTP response code.

        A check fail is considered of high severity and as such will raise a ScenarioCannotContinueError.

        :return: the DSS response
        """

        isas = fetch.isas(
            area=area,
            start_time=start_time,
            end_time=end_time,
            rid_version=self._dss.rid_version,
            session=self._dss.client,
            participant_id=self._dss.participant_id,
        )

        self.handle_query_result(
            check=main_check,
            q=isas,
            required_status_code=expected_error_codes,
            fail_msg=f"Searching for ISAs resulted in an HTTP code not in {expected_error_codes}",
            fail_details=f"Search area: {area}; from {start_time} to {end_time}",
        )

        return isas

    def get_isa(
        self,
        check: PendingCheck,
        isa_id: str,
    ) -> FetchedISA:
        """Get an ISA at the DSS.
        A check fail is considered of high severity and as such will raise a ScenarioCannotContinueError.
        Fails if the ID of the ISA returned by the DSS does not match the requested ID.

        :return: the DSS response
        """

        try:
            isa = fetch.isa(
                isa_id=isa_id,
                rid_version=self._dss.rid_version,
                session=self._dss.client,
                participant_id=self._dss.participant_id,
            )

            self.handle_query_result(check, isa, f"Failed to get ISA {isa_id}")

            if isa_id != isa.isa.id:
                check.record_failed(
                    summary=f"DSS did not return correct ISA",
                    severity=Severity.High,
                    details=f"Expected ISA ID {isa_id} but got {isa.id}",
                    query_timestamps=[isa.query.request.timestamp],
                )
            else:
                return isa

        except QueryError as e:
            self._handle_query_error(check, e)
        raise RuntimeError(
            "DSS query was not successful, but a High Severity issue didn't interrupt execution"
        )

    def get_isa_expect_response_code(
        self,
        check: PendingCheck,
        expected_error_codes: Set[int],
        isa_id: str,
    ) -> FetchedISA:
        """Attempt to fetch an ISA at the DSS, and expect the specified HTTP response code.

        A check fail is considered of high severity and as such will raise a ScenarioCannotContinueError.

        :return: the DSS response
        """

        isa = fetch.isa(
            isa_id=isa_id,
            rid_version=self._dss.rid_version,
            session=self._dss.client,
            participant_id=self._dss.participant_id,
        )

        self.handle_query_result(
            check=check,
            q=isa,
            required_status_code=expected_error_codes,
            fail_msg=f"Fetching ISA {isa_id} resulted in an HTTP code not in {expected_error_codes}",
            fail_details=f"ISA: ID {isa_id}",
        )

        return isa

    def put_isa_expect_response_code(
        self,
        check: PendingCheck,
        expected_error_codes: Set[int],
        area_vertices: List[s2sphere.LatLng],
        alt_lo: float,
        alt_hi: float,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        uss_base_url: str,
        isa_id: str,
        isa_version: Optional[str] = None,
    ) -> ISAChange:
        mutated_isa = mutate.put_isa(
            area_vertices=area_vertices,
            alt_lo=alt_lo,
            alt_hi=alt_hi,
            start_time=start_time,
            end_time=end_time,
            uss_base_url=uss_base_url,
            isa_id=isa_id,
            isa_version=isa_version,
            rid_version=self._dss.rid_version,
            utm_client=self._dss.client,
            participant_id=self._dss.participant_id,
        )

        for notification_query in mutated_isa.notifications.values():
            self._scenario.record_query(notification_query.query)

        self.handle_query_result(
            check=check,
            q=mutated_isa.dss_query,
            fail_msg="ISA Put succeeded when expecting a failure",
            required_status_code=expected_error_codes,
            severity=Severity.High,
            fail_details=f"The submitted query was expected to fail. Payload: {mutated_isa.dss_query.query.request.json}",
        )
        return mutated_isa

    def put_isa(
        self,
        main_check: PendingCheck,
        area_vertices: List[s2sphere.LatLng],
        alt_lo: float,
        alt_hi: float,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        uss_base_url: str,
        isa_id: str,
        isa_version: Optional[str] = None,
    ) -> ISAChange:
        """Create or update an ISA at the DSS.

        Query failure will fail the provided main check. If the query is successful, the sub-checks of the test step
        described in '[v19|v22a]/dss/test_steps/put_isa.md' are performed. Some of those might fail the main check.

        :return: the DSS response
        """

        mutated_isa = mutate.put_isa(
            area_vertices=area_vertices,
            alt_lo=alt_lo,
            alt_hi=alt_hi,
            start_time=start_time,
            end_time=end_time,
            uss_base_url=uss_base_url,
            isa_id=isa_id,
            isa_version=isa_version,
            rid_version=self._dss.rid_version,
            utm_client=self._dss.client,
            participant_id=self._dss.participant_id,
        )
        self.handle_query_result(
            main_check, mutated_isa.dss_query, f"Failed to insert ISA {isa_id}"
        )
        for notification_query in mutated_isa.notifications.values():
            self._scenario.record_query(notification_query.query)

        dss_id = [self._dss.participant_id]
        t_dss = mutated_isa.dss_query.query.request.timestamp

        # sub-checks that do not fail the main check
        with self._scenario.check("ISA response code", dss_id) as sub_check:
            if mutated_isa.dss_query.query.status_code == 201:
                sub_check.record_failed(
                    summary=f"PUT ISA returned technically-incorrect 201",
                    severity=Severity.Low,
                    details="DSS should return 200 from PUT ISA, but instead returned the reasonable-but-technically-incorrect code 201",
                    query_timestamps=[t_dss],
                )

        isa_validator = ISAValidator(
            main_check=main_check,
            scenario=self._scenario,
            isa_params=dict(
                area_vertices=area_vertices,
                start_time=start_time,
                end_time=end_time,
                uss_base_url=uss_base_url,
                alt_lo=alt_lo,
                alt_hi=alt_hi,
            ),
            dss_id=dss_id,
            rid_version=self._dss.rid_version,
        )

        isa_validator.validate_mutated_isa(
            isa_id, mutated_isa.dss_query, previous_version=None
        )
        # TODO: Validate subscriber notifications (the validator currently does not)

        return mutated_isa

    def del_isa(
        self,
        main_check: PendingCheck,
        isa_id: str,
        isa_version: str,
    ) -> ISAChange:
        """Delete an ISA at the DSS.

        Query failure will fail the provided main check. If the query is successful, the sub-checks of the test step
        described in '[v19|v22a]/dss/test_steps/delete_isa.md' are performed. Some of those might fail the main check.

        :return: the DSS response
        """

        del_isa = mutate.delete_isa(
            isa_id=isa_id,
            isa_version=isa_version,
            rid_version=self._dss.rid_version,
            utm_client=self._dss.client,
            participant_id=self._dss.participant_id,
        )
        self.handle_query_result(
            main_check, del_isa.dss_query, f"Failed to delete ISA {isa_id}"
        )
        for notification_query in del_isa.notifications.values():
            self._scenario.record_query(notification_query.query)

        dss_id = [self._dss.participant_id]
        t_dss = del_isa.dss_query.query.request.timestamp
        dss_isa = del_isa.dss_query.isa

        # sub-checks that do not fail the main check
        with self._scenario.check("ISA response format", dss_id) as sub_check:
            errors = schema_validation.validate(
                self._dss.rid_version.openapi_path,
                self._dss.rid_version.openapi_delete_isa_response_path,
                del_isa.dss_query.query.response.json,
            )
            if errors:
                details = "\n".join(f"[{e.json_path}] {e.message}" for e in errors)
                sub_check.record_failed(
                    "Delete ISA response format was invalid",
                    Severity.Medium,
                    "Found the following schema validation errors in the DSS response:\n"
                    + details,
                    query_timestamps=[t_dss],
                )

        # sub-checks that fail the main check
        def _fail_sub_check(
            _sub_check: PendingCheck, _summary: str, _details: str
        ) -> None:
            """Fails with Medium severity the sub_check and with High severity the main check."""

            _sub_check.record_failed(
                summary=_summary,
                severity=Severity.Medium,
                details=_details,
                query_timestamps=[t_dss],
            )
            main_check.record_failed(
                summary=f"Delete ISA request succeeded, but the DSS response is not valid: {_summary}",
                severity=Severity.High,
                details=_details,
                query_timestamps=[t_dss],
            )

        with self._scenario.check("ISA ID matches", dss_id) as sub_check:
            if isa_id != dss_isa.id:
                _fail_sub_check(
                    sub_check,
                    "Deleted ISA ID did not match",
                    f"Expected ISA ID {isa_id} but got {dss_isa.id}",
                )

        with self._scenario.check("ISA version matches", dss_id) as sub_check:
            if dss_isa.version != isa_version:
                _fail_sub_check(
                    sub_check,
                    "Deleted ISA version did not match",
                    f"Expected ISA version {isa_version} but got {dss_isa.version}",
                )

        isa_validator = ISAValidator(
            main_check=main_check,
            scenario=self._scenario,
            isa_params=None,  # won't check the ISA's content
            dss_id=dss_id,
            rid_version=self._dss.rid_version,
        )

        isa_validator.validate_deleted_isa(
            isa_id, del_isa.dss_query, expected_version=isa_version
        )

        return del_isa

    def del_isa_expect_response_code(
        self,
        main_check: PendingCheck,
        expected_error_codes: Set[int],
        isa_id: str,
        isa_version: str,
    ) -> ISAChange:
        """Attempt to delete an ISA at the DSS, and expect the specified HTTP response code.

        A check fail is considered of high severity and as such will raise a ScenarioCannotContinueError.

        :return: the DSS response
        """

        del_isa = mutate.delete_isa(
            isa_id=isa_id,
            isa_version=isa_version,
            rid_version=self._dss.rid_version,
            utm_client=self._dss.client,
            participant_id=self._dss.participant_id,
        )

        for notification_query in del_isa.notifications.values():
            self._scenario.record_query(notification_query.query)

        self.handle_query_result(
            check=main_check,
            q=del_isa.dss_query,
            required_status_code=expected_error_codes,
            fail_msg=f"Deleting ISA {isa_id} resulted in an HTTP code not in {expected_error_codes}",
            fail_details=f"ISA: ID {isa_id}; version {isa_version}",
        )

        return del_isa

    def cleanup_isa(
        self,
        check: PendingCheck,
        isa_id: str,
    ) -> Optional[ISAChange]:
        """Cleanup an ISA at the DSS. Does not fail if the ISA is not found.
        A check fail is considered of medium severity and won't raise error.

        :return: the DSS response if the ISA exists
        """
        try:
            isa = fetch.isa(
                isa_id=isa_id,
                rid_version=self._dss.rid_version,
                session=self._dss.client,
                participant_id=self._dss.participant_id,
            )

            self.handle_query_result(
                check, isa, f"Failed to get ISA {isa_id}", {404, 200}, Severity.Medium
            )

            if isa.status_code == 404:
                return None

            del_isa = mutate.delete_isa(
                isa_id=isa_id,
                isa_version=isa.isa.version,
                rid_version=self._dss.rid_version,
                utm_client=self._dss.client,
                participant_id=self._dss.participant_id,
            )

            self.handle_query_result(
                check,
                del_isa.dss_query,
                f"Failed to delete ISA {isa_id}",
                {404, 200},
                Severity.Medium,
            )

            return del_isa

        except QueryError as e:
            self._handle_query_error(check, e)
        raise RuntimeError(
            "DSS query was not successful, but a High Severity issue didn't interrupt execution"
        )

    def search_subs_expect_response_code(
        self,
        check: PendingCheck,
        expected_codes: Set[int],
        area: List[s2sphere.LatLng],
    ) -> FetchedSubscriptions:
        """Search for subscriptions at the DSS, expecting one of the passed HTTP response codes.

        :return: anything the DSS responded with if the response code was as expected
        """
        try:
            subs = fetch.subscriptions(
                area=area,
                rid_version=self._dss.rid_version,
                session=self._dss.client,
                participant_id=self._dss.participant_id,
            )

            self.handle_query_result(
                check=check,
                q=subs,
                fail_msg=f"Search for subscriptions in area {area} failed to yield a result code in {expected_codes}",
                required_status_code=expected_codes,
            )
            return subs

        except QueryError as e:
            self._handle_query_error(check, e)
        raise RuntimeError(
            "DSS query was not successful, but a High Severity issue didn't interrupt execution"
        )

    def search_subs(
        self,
        check: PendingCheck,
        area: List[s2sphere.LatLng],
    ) -> FetchedSubscriptions:
        """Search for subscriptions at the DSS.
        A check fail is considered of high severity and as such will raise a ScenarioCannotContinueError.

        :return: the DSS response
        """

        try:
            subs = fetch.subscriptions(
                area=area,
                rid_version=self._dss.rid_version,
                session=self._dss.client,
                participant_id=self._dss.participant_id,
            )

            self.handle_query_result(
                check, subs, f"Failed to search subscriptions in {area}"
            )
            return subs

        except QueryError as e:
            self._handle_query_error(check, e)
        raise RuntimeError(
            "DSS query was not successful, but a High Severity issue didn't interrupt execution"
        )

    def get_sub_expect_response_code(
        self,
        check: PendingCheck,
        expected_response_codes: Set[int],
        sub_id: str,
    ) -> FetchedSubscription:
        """Get a subscription at the DSS, expecting one the passed HTTP response codes.

        :return: anything the DSS responded with if the response code was as expected
        """
        try:
            sub = fetch.subscription(
                subscription_id=sub_id,
                rid_version=self._dss.rid_version,
                session=self._dss.client,
                participant_id=self._dss.participant_id,
            )

            self.handle_query_result(
                check=check,
                q=sub,
                fail_msg=f"The request to get subscription with ID {sub_id} yielded a response code that wasn't in {expected_response_codes}",
                required_status_code=expected_response_codes,
            )

            return sub

        except QueryError as e:
            self._handle_query_error(check, e)
        raise RuntimeError(
            "DSS query was not successful, but a High Severity issue didn't interrupt execution"
        )

    def get_sub(
        self,
        check: PendingCheck,
        sub_id: str,
    ) -> FetchedSubscription:
        """Get a subscription at the DSS.
        A check fail is considered of high severity and as such will raise a ScenarioCannotContinueError.
        Fails if the ID of the subscription returned by the DSS does not match the requested ID.

        :return: the DSS response
        """

        try:
            sub = fetch.subscription(
                subscription_id=sub_id,
                rid_version=self._dss.rid_version,
                session=self._dss.client,
                participant_id=self._dss.participant_id,
            )

            self.handle_query_result(check, sub, f"Failed to get subscription {sub_id}")

            if sub_id != sub.subscription.id:
                check.record_failed(
                    summary=f"DSS did not return correct subscription",
                    severity=Severity.High,
                    details=f"Expected Subscription ID {sub_id} but got {sub.subscription.id}",
                    query_timestamps=[sub.query.request.timestamp],
                )
            else:
                return sub

        except QueryError as e:
            self._handle_query_error(check, e)
        raise RuntimeError(
            "DSS query was not successful, but a High Severity issue didn't interrupt execution"
        )

    def no_sub(
        self,
        check: PendingCheck,
        sub_id: str,
    ):
        """Ensure a subscription does not exist at the DSS.
        A check fail is considered of high severity and as such will raise a ScenarioCannotContinueError.

        :return: the DSS response
        """

        try:
            sub = fetch.subscription(
                subscription_id=sub_id,
                rid_version=self._dss.rid_version,
                session=self._dss.client,
                participant_id=self._dss.participant_id,
            )

            self.handle_query_result(
                check, sub, f"Failed to get subscription {sub_id}", {404}
            )
            return

        except QueryError as e:
            self._handle_query_error(check, e)
        raise RuntimeError(
            "DSS query was not successful, but a High Severity issue didn't interrupt execution"
        )

    def put_sub_expect_response_code(
        self,
        check: PendingCheck,
        area_vertices: List[s2sphere.LatLng],
        alt_lo: float,
        alt_hi: float,
        start_time: Optional[datetime.datetime],
        end_time: Optional[datetime.datetime],
        expected_error_codes: Set[int],
        uss_base_url: str,
        sub_id: str,
        sub_version: Optional[str] = None,
    ) -> ChangedSubscription:
        """Attempt to create or update a subscription at the DSS, and expect the specified HTTP response code.

        :return: anything the DSS responded with if the response code was as expected
        """
        try:
            created_sub = mutate.upsert_subscription(
                area_vertices=area_vertices,
                alt_lo=alt_lo,
                alt_hi=alt_hi,
                start_time=start_time,
                end_time=end_time,
                uss_base_url=uss_base_url,
                subscription_id=sub_id,
                subscription_version=sub_version,
                rid_version=self._dss.rid_version,
                utm_client=self._dss.client,
                participant_id=self._dss.participant_id,
            )

            self.handle_query_result(
                check=check,
                q=created_sub,
                required_status_code=expected_error_codes,
                fail_msg=f"Inserting subscription {sub_id} had an http code not in {expected_error_codes}",
                fail_details=f"Passed subscription start and end times: {start_time} - {end_time} (duration: {end_time - start_time})"
                f"altitudes: {alt_lo} - {alt_hi}, area: {area_vertices}",
            )
            return created_sub

        except QueryError as e:
            self._handle_query_error(check, e)
        raise RuntimeError(
            "DSS query was not successful, but a High Severity issue didn't interrupt execution"
        )

    def put_sub(
        self,
        check: PendingCheck,
        area_vertices: List[s2sphere.LatLng],
        alt_lo: float,
        alt_hi: float,
        start_time: Optional[datetime.datetime],
        end_time: Optional[datetime.datetime],
        uss_base_url: str,
        sub_id: str,
        sub_version: Optional[str] = None,
    ) -> ChangedSubscription:
        """Create or update a subscription at the DSS.
        A check fail is considered of high severity and as such will raise a ScenarioCannotContinueError.

        :return: the DSS response
        """

        try:
            created_sub = mutate.upsert_subscription(
                area_vertices=area_vertices,
                alt_lo=alt_lo,
                alt_hi=alt_hi,
                start_time=start_time,
                end_time=end_time,
                uss_base_url=uss_base_url,
                subscription_id=sub_id,
                subscription_version=sub_version,
                rid_version=self._dss.rid_version,
                utm_client=self._dss.client,
                participant_id=self._dss.participant_id,
            )

            self.handle_query_result(
                check, created_sub, f"Failed to insert subscription {sub_id}"
            )
            return created_sub

        except QueryError as e:
            self._handle_query_error(check, e)
        raise RuntimeError(
            "DSS query was not successful, but a High Severity issue didn't interrupt execution"
        )

    def del_sub_expect_response_code(
        self,
        check: PendingCheck,
        expected_response_codes: Set[int],
        sub_id: str,
        sub_version: str,
    ) -> ChangedSubscription:
        """Attempts to delete a subscription at the DSS,
        and verifies that the response code is part of the expected ones.

        :return: anything the DSS responded with if the response code was as expected
        """

        try:
            del_sub = mutate.delete_subscription(
                subscription_id=sub_id,
                subscription_version=sub_version,
                rid_version=self._dss.rid_version,
                utm_client=self._dss.client,
                participant_id=self._dss.participant_id,
            )

            self.handle_query_result(
                check=check,
                q=del_sub,
                fail_msg=f"Query to delete subscription with ID {sub_id} wit not yield a response code in {expected_response_codes}",
                required_status_code=expected_response_codes,
            )

            return del_sub
        except QueryError as e:
            self._handle_query_error(check, e)
        raise RuntimeError(
            "DSS query was not successful, but a High Severity issue didn't interrupt execution"
        )

    def del_sub(
        self,
        check: PendingCheck,
        sub_id: str,
        sub_version: str,
    ) -> ChangedSubscription:
        """Delete a subscription at the DSS.
        A check fail is considered of high severity and as such will raise a ScenarioCannotContinueError.

        :return: the DSS response
        """

        try:
            del_sub = mutate.delete_subscription(
                subscription_id=sub_id,
                subscription_version=sub_version,
                rid_version=self._dss.rid_version,
                utm_client=self._dss.client,
                participant_id=self._dss.participant_id,
            )

            self.handle_query_result(
                check, del_sub, f"Failed to delete subscription {sub_id}"
            )

            if sub_version != del_sub.subscription.version:
                check.record_failed(
                    summary=f"Deleted subscription did not match",
                    severity=Severity.High,
                    details=f"DSS reported deletion of version {sub_version} while expecting {del_sub.subscription.version}",
                    query_timestamps=[del_sub.query.request.timestamp],
                )
            else:
                return del_sub

        except QueryError as e:
            self._handle_query_error(check, e)
        raise RuntimeError(
            "DSS query was not successful, but a High Severity issue didn't interrupt execution"
        )

    def cleanup_subs_in_area(
        self,
        area: List[s2sphere.LatLng],
    ):
        """Cleanup any subscription that is returned for the search in the provided area"""

        with self._scenario.check(
            "Successful subscription search query", [self.participant_id]
        ) as check:
            found_subs = self.search_subs(check, area)

        try:
            for sub_id, sub in found_subs.subscriptions.items():
                with self._scenario.check(
                    "Subscription can be deleted", [self.participant_id]
                ) as check:
                    del_sub = mutate.delete_subscription(
                        subscription_id=sub_id,
                        subscription_version=sub.version,
                        rid_version=self._dss.rid_version,
                        utm_client=self._dss.client,
                        participant_id=self._dss.participant_id,
                    )

                    self.handle_query_result(
                        check,
                        del_sub,
                        f"Failed to delete subscription {sub}",
                        {404, 200},
                        Severity.Medium,
                    )
        except QueryError as e:
            self._handle_query_error(check, e)
            raise RuntimeError(
                "DSS query was not successful, but a High Severity issue didn't interrupt execution"
            )

    def cleanup_sub(
        self,
        sub_id: str,
    ) -> Optional[ChangedSubscription]:
        """Cleanup a subscription at the DSS. Does not fail if it is not found.
        A check fail is considered of medium severity and won't raise error.

        :return: the DSS response if the subscription exists
        """
        try:
            with self._scenario.check(
                "Subscription can be queried by ID", [self.participant_id]
            ) as check:
                sub = fetch.subscription(
                    subscription_id=sub_id,
                    rid_version=self._dss.rid_version,
                    session=self._dss.client,
                    participant_id=self._dss.participant_id,
                )

                self.handle_query_result(
                    check,
                    sub,
                    f"Failed to get subscription {sub_id}",
                    {404, 200},
                    Severity.Medium,
                )

            if sub.status_code == 404:
                return None

            with self._scenario.check(
                "Subscription can be deleted", [self.participant_id]
            ) as check:
                del_sub = mutate.delete_subscription(
                    subscription_id=sub_id,
                    subscription_version=sub.subscription.version,
                    rid_version=self._dss.rid_version,
                    utm_client=self._dss.client,
                    participant_id=self._dss.participant_id,
                )

                self.handle_query_result(
                    check,
                    del_sub,
                    f"Failed to delete subscription {sub_id}",
                    {404, 200},
                    Severity.Medium,
                )

            return del_sub

        except QueryError as e:
            self._handle_query_error(check, e)
        raise RuntimeError(
            "DSS query was not successful, but a High Severity issue didn't interrupt execution"
        )

    def raw_request_with_expected_code(
        self,
        check: PendingCheck,
        method: str,
        url_path: str,
        json: Dict[str, Any],
        expected_error_codes: Set[int],
        fail_msg: str,
    ) -> RIDQuery:
        """For passing raw requests to the underlying client.
        Mostly useful for sending malformed requests when testing validations.
        """

        req_descr = RequestDescription(
            method=method,
            url=url_path,
            json=json,
            timestamp=datetime.datetime.utcnow(),
        )

        resp = self._dss.client.put(url_path, json=json)

        q = Query(
            request=req_descr,
            response=ResponseDescription(
                code=resp.status_code,
                json=resp.json(),
                body=resp.content,
                headers=resp.headers,
                reported=StringBasedDateTime(datetime.datetime.utcnow()),
            ),
        )
        self._scenario.record_query(q)

        if self._dss.rid_version == RIDVersion.f3411_19:
            rid_query = RIDQuery(v19_query=q)
        elif self._dss.rid_version == RIDVersion.f3411_22a:
            rid_query = RIDQuery(v22a_query=q)
        else:
            raise ValueError(f"Unknown RID version: {self._dss.rid_version}")

        self.handle_query_result(
            check,
            rid_query,
            fail_msg,
            expected_error_codes,
            Severity.Medium,
        )

        return rid_query
