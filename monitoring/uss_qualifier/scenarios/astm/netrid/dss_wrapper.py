import datetime
import s2sphere

from typing import Optional, List, Set

from monitoring.monitorlib import schema_validation
from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.fetch.rid import (
    FetchedSubscription,
    FetchedSubscriptions,
    RIDQuery,
    FetchedISA,
    FetchedISAs,
)
from monitoring.monitorlib.mutate import rid as mutate
from monitoring.monitorlib.fetch import rid as fetch
from monitoring.monitorlib.mutate.rid import ISAChange, ChangedSubscription
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstance
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
            participants=[self._dss.participant_id],
            severity=Severity.High,
            details=f"{str(e)}\n\nStack trace:\n{e.stacktrace}",
            query_timestamps=[q.request.timestamp for q in e.queries],
        )

    def _handle_query_result(
        self,
        check: PendingCheck,
        q: RIDQuery,
        fail_msg: str,
        required_status_code: Optional[Set[int]] = None,
        severity: Severity = Severity.High,
        fail_details: Optional[str] = None,
    ):
        """
        :param required_status_code: one of those status code is expected, overrides the success check
        """
        self._scenario.record_query(q.query)
        if (required_status_code is None and not q.success) or (
            required_status_code is not None
            and q.status_code not in required_status_code
        ):
            check.record_failed(
                summary=fail_msg,
                severity=severity,
                participants=[self._dss.participant_id],
                details=f"{fail_details}\n{q.status_code} response: "
                + "\n".join(q.errors)
                if fail_details is not None
                else f"{q.status_code} response: " + "\n".join(q.errors),
                query_timestamps=[q.query.request.timestamp],
            )

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
                server_id=self._dss.participant_id,
            )

            self._handle_query_result(check, isa, f"Failed to get ISA {isa_id}")

            if isa_id != isa.isa.id:
                check.record_failed(
                    summary=f"DSS did not return correct ISA",
                    severity=Severity.High,
                    participants=[self._dss.participant_id],
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
            server_id=self._dss.participant_id,
        )
        self._handle_query_result(
            main_check, mutated_isa.dss_query, f"Failed to insert ISA {isa_id}"
        )
        for notification_query in mutated_isa.notifications.values():
            self._scenario.record_query(notification_query.query)

        dss_id = [self._dss.participant_id]
        t_dss = mutated_isa.dss_query.query.request.timestamp
        dss_isa = mutated_isa.dss_query.isa

        # sub-checks that do not fail the main check
        with self._scenario.check("ISA response code", dss_id) as sub_check:
            if mutated_isa.dss_query.query.status_code == 201:
                sub_check.record_failed(
                    summary=f"PUT ISA returned technically-incorrect 201",
                    severity=Severity.Low,
                    details="DSS should return 200 from PUT ISA, but instead returned the reasonable-but-technically-incorrect code 201",
                    query_timestamps=[t_dss],
                )

        with self._scenario.check("ISA response format", dss_id) as sub_check:
            errors = schema_validation.validate(
                self._dss.rid_version.openapi_path,
                self._dss.rid_version.openapi_put_isa_response_path,
                mutated_isa.dss_query.query.response.json,
            )
            if errors:
                details = "\n".join(f"[{e.json_path}] {e.message}" for e in errors)
                sub_check.record_failed(
                    "PUT ISA response format was invalid",
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
                summary=f"PUT ISA request succeeded, but the DSS response is not valid: {_summary}",
                severity=Severity.High,
                details=_details,
                query_timestamps=[t_dss],
            )

        with self._scenario.check("ISA ID matches", dss_id) as sub_check:
            if isa_id != dss_isa.id:
                _fail_sub_check(
                    sub_check,
                    "DSS did not return correct ISA",
                    f"Expected ISA ID {isa_id} but got {dss_isa.id}",
                )

        if isa_version is not None:
            with self._scenario.check("ISA version changed", dss_id) as sub_check:
                if dss_isa.version == isa_version:
                    _fail_sub_check(
                        sub_check,
                        "ISA was not modified",
                        f"Got old version {isa_version} while expecting new version",
                    )

        with self._scenario.check("ISA version format", dss_id) as sub_check:
            if not all(c not in "\0\t\r\n#%/:?@[\]" for c in dss_isa.version):
                _fail_sub_check(
                    sub_check,
                    f"DSS returned ISA (ID {isa_id}) with invalid version format",
                    f"DSS returned an ISA with a version that is not URL-safe: {dss_isa.version}",
                )

        with self._scenario.check("ISA start time matches", dss_id) as sub_check:
            if abs((dss_isa.time_start - start_time).total_seconds()) > MAX_SKEW:
                _fail_sub_check(
                    sub_check,
                    f"DSS returned ISA (ID {isa_id}) with incorrect start time",
                    f"DSS should have returned an ISA with a start time of {start_time}, but instead the ISA returned had a start time of {dss_isa.time_start}",
                )

        with self._scenario.check("ISA end time matches", dss_id) as sub_check:
            if abs((dss_isa.time_end - end_time).total_seconds()) > MAX_SKEW:
                _fail_sub_check(
                    sub_check,
                    f"DSS returned ISA (ID {isa_id}) with incorrect end time",
                    f"DSS should have returned an ISA with an end time of {end_time}, but instead the ISA returned had an end time of {dss_isa.time_end}",
                )

        with self._scenario.check("ISA URL matches", dss_id) as sub_check:
            expected_flights_url = self._dss.rid_version.flights_url_of(uss_base_url)
            actual_flights_url = dss_isa.flights_url
            if actual_flights_url != expected_flights_url:
                _fail_sub_check(
                    sub_check,
                    f"DSS returned ISA (ID {isa_id}) with incorrect URL",
                    f"DSS should have returned an ISA with a flights URL of {expected_flights_url}, but instead the ISA returned had a flights URL of {actual_flights_url}",
                )

        # TODO: Validate subscriber notifications

        return mutated_isa

    def del_isa(
        self,
        check: PendingCheck,
        isa_id: str,
        isa_version: str,
    ) -> ISAChange:
        """Delete an ISA at the DSS.
        A check fail is considered of high severity and as such will raise a ScenarioCannotContinueError.

        :return: the DSS response
        """

        try:
            del_isa = mutate.delete_isa(
                isa_id=isa_id,
                isa_version=isa_version,
                rid_version=self._dss.rid_version,
                utm_client=self._dss.client,
                server_id=self._dss.participant_id,
            )

            self._handle_query_result(
                check, del_isa.dss_query, f"Failed to delete ISA {isa_id}"
            )

            if isa_version != del_isa.dss_query.isa.version:
                check.record_failed(
                    summary=f"Deleted ISA did not match",
                    severity=Severity.High,
                    participants=[self._dss.participant_id],
                    details=f"DSS reported deletion of version {isa_version} while expecting {del_isa.dss_query.isa.version}",
                    query_timestamps=[del_isa.dss_query.query.request.timestamp],
                )
            else:
                return del_isa

        except QueryError as e:
            self._handle_query_error(check, e)
        raise RuntimeError(
            "DSS query was not successful, but a High Severity issue didn't interrupt execution"
        )

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
                server_id=self._dss.participant_id,
            )

            self._handle_query_result(
                check, isa, f"Failed to get ISA {isa_id}", {404, 200}, Severity.Medium
            )

            if isa.status_code == 404:
                return None

            del_isa = mutate.delete_isa(
                isa_id=isa_id,
                isa_version=isa.isa.version,
                rid_version=self._dss.rid_version,
                utm_client=self._dss.client,
                server_id=self._dss.participant_id,
            )

            self._handle_query_result(
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
                server_id=self._dss.participant_id,
            )

            self._handle_query_result(
                check, subs, f"Failed to search subscriptions in {area}"
            )
            return subs

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
                server_id=self._dss.participant_id,
            )

            self._handle_query_result(
                check, sub, f"Failed to get subscription {sub_id}"
            )

            if sub_id != sub.subscription.id:
                check.record_failed(
                    summary=f"DSS did not return correct subscription",
                    severity=Severity.High,
                    participants=[self._dss.participant_id],
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
                server_id=self._dss.participant_id,
            )

            self._handle_query_result(
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
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        expected_error_codes: Set[int],
        uss_base_url: str,
        sub_id: str,
        sub_version: Optional[str] = None,
    ) -> ChangedSubscription:
        """Attempt to create or update a subscription at the DSS, and expect the specified HTTP response code.

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
                server_id=self._dss.participant_id,
            )

            self._handle_query_result(
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
        start_time: datetime.datetime,
        end_time: datetime.datetime,
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
                server_id=self._dss.participant_id,
            )

            self._handle_query_result(
                check, created_sub, f"Failed to insert subscription {sub_id}"
            )
            return created_sub

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
                server_id=self._dss.participant_id,
            )

            self._handle_query_result(
                check, del_sub, f"Failed to delete subscription {sub_id}"
            )

            if sub_version != del_sub.subscription.version:
                check.record_failed(
                    summary=f"Deleted subscription did not match",
                    severity=Severity.High,
                    participants=[self._dss.participant_id],
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

    def cleanup_sub(
        self,
        check: PendingCheck,
        sub_id: str,
    ) -> Optional[ChangedSubscription]:
        """Cleanup a subscription at the DSS. Does not fail if it is not found.
        A check fail is considered of medium severity and won't raise error.

        :return: the DSS response if the subscription exists
        """
        try:
            sub = fetch.subscription(
                subscription_id=sub_id,
                rid_version=self._dss.rid_version,
                session=self._dss.client,
                server_id=self._dss.participant_id,
            )

            self._handle_query_result(
                check,
                sub,
                f"Failed to get subscription {sub_id}",
                {404, 200},
                Severity.Medium,
            )

            if sub.status_code == 404:
                return None

            del_sub = mutate.delete_subscription(
                subscription_id=sub_id,
                subscription_version=sub.subscription.version,
                rid_version=self._dss.rid_version,
                utm_client=self._dss.client,
                server_id=self._dss.participant_id,
            )

            self._handle_query_result(
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
