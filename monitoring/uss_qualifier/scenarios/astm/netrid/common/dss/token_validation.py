import datetime
from typing import Optional, Dict, List

import arrow
import s2sphere
from uas_standards.astm.f3411 import v19, v22a

from monitoring.monitorlib import fetch, infrastructure
from monitoring.monitorlib import rid_v1, rid_v2
from monitoring.monitorlib.auth import InvalidTokenSignatureAuth
from monitoring.monitorlib.fetch import rid as rid_fetch
from monitoring.monitorlib.fetch.rid import FetchedISA, FetchedISAs
from monitoring.monitorlib.mutate import rid as mutate
from monitoring.monitorlib.mutate.rid import (
    ISAChange,
    ChangedISA,
    ISAChangeNotification,
)
from monitoring.monitorlib.rid import RIDVersion
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.resources.netrid.service_area import ServiceAreaResource
from monitoring.uss_qualifier.scenarios.astm.netrid.common.dss.isa_simple import (
    ISASimple,
)
from monitoring.uss_qualifier.scenarios.astm.netrid.dss_wrapper import DSSWrapper
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class TokenValidation(GenericTestScenario):
    """Based on prober/rid/v2/test_token_validation.py from the legacy prober tool."""

    ISA_TYPE = register_resource_type(372, "ISA")

    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        isa: ServiceAreaResource,
    ):
        super().__init__()
        self._dss = dss.dss_instance
        self._dss_wrapper = DSSWrapper(self, dss.dss_instance)
        self._isa_id = id_generator.id_factory.make_id(ISASimple.ISA_TYPE)
        self._isa_version: Optional[str] = None
        self._isa = isa.specification

        now = arrow.utcnow().datetime
        self._isa_start_time = self._isa.shifted_time_start(now)
        self._isa_end_time = self._isa.shifted_time_end(now)
        self._isa_area = [vertex.as_s2sphere() for vertex in self._isa.footprint]

        # correctly formed and signed using an unrecognized private key
        # (should cause requests to be rejected)
        self._unsigned_token_session = infrastructure.UTMClientSession(
            self._dss.base_url, InvalidTokenSignatureAuth()
        )
        # Session that won't provide a token at all
        # (should cause requests to be rejected)
        self._no_token_session = infrastructure.UTMClientSession(
            self._dss.base_url, None
        )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.begin_test_case("Setup")
        self.begin_test_step("Ensure clean workspace")
        self._delete_isa_if_exists()
        self.end_test_step()
        self.end_test_case()

        self.begin_test_case("Token validation")
        self.begin_test_step("Token validation")

        self._wrong_auth_put()
        self._create_isa()
        self._wrong_auth_get()
        self._wrong_auth_mutate()
        self._wrong_auth_search()
        self._wrong_auth_delete()
        self._delete_isa()

        self.end_test_step()
        self.end_test_case()

        self.end_test_scenario()

    def _wrong_auth_put(self):
        # Try to create an ISA with a read scope
        put_wrong_scope = self._put_isa_tweak_auth(
            utm_client=self._dss.client,
            scope_intent="read",
        )
        with self.check(
            "Read scope cannot create an ISA", participants=[self._dss.participant_id]
        ) as check:
            if put_wrong_scope.dss_query.success:
                check.record_failed(
                    "Read scope can create ISA",
                    Severity.High,
                    f"Attempting to create ISA {self._isa_id} with read scope returned {put_wrong_scope.dss_query.status_code}",
                    query_timestamps=[
                        put_wrong_scope.dss_query.query.request.timestamp
                    ],
                )

        # Try to create an ISA with a missing token
        put_no_token = self._put_isa_tweak_auth(
            utm_client=self._no_token_session,
            scope_intent="write",
        )

        with self.check(
            "Missing token prevents creating an ISA",
            participants=[self._dss.participant_id],
        ) as check:
            if put_no_token.dss_query.success:
                check.record_failed(
                    "Could create an ISA without a token",
                    Severity.High,
                    f"Attempting to create ISA {self._isa_id} with no token returned {put_no_token.dss_query.status_code}",
                    query_timestamps=[put_no_token.dss_query.query.request.timestamp],
                )

        # Try to create an ISA with a fake token
        put_fake_token = self._put_isa_tweak_auth(
            utm_client=self._unsigned_token_session,
            scope_intent="write",
        )

        with self.check(
            "Fake token prevents creating an ISA",
            participants=[self._dss.participant_id],
        ) as check:
            if put_fake_token.dss_query.success:
                check.record_failed(
                    "Could create an ISA with a fake token",
                    Severity.High,
                    f"Attempting to create ISA {self._isa_id} with a fake token returned {put_fake_token.dss_query.status_code}",
                    query_timestamps=[put_fake_token.dss_query.query.request.timestamp],
                )

    def _create_isa(self):
        with self.check(
            "Correct token and scope can create ISA", [self._dss_wrapper.participant_id]
        ) as check:
            new_isa = self._dss_wrapper.put_isa(
                main_check=check,
                area_vertices=self._isa_area,
                start_time=self._isa_start_time,
                end_time=self._isa_end_time,
                uss_base_url=self._isa.base_url,
                isa_id=self._isa_id,
                isa_version=self._isa_version,
                alt_lo=self._isa.altitude_min,
                alt_hi=self._isa.altitude_max,
            )
            self._isa_version = new_isa.dss_query.isa.version

    def _wrong_auth_get(self):

        get_no_token = self._get_isa_tweak_auth(self._no_token_session)
        with self.check(
            "Missing token prevents reading an ISA",
            participants=[self._dss.participant_id],
        ) as check:
            if get_no_token.success:
                check.record_failed(
                    "Could read an ISA without a token",
                    Severity.High,
                    f"Attempting to read ISA {self._isa_id} with no token returned {get_no_token.status_code}",
                    query_timestamps=[get_no_token.query.request.timestamp],
                )

        get_fake_token = self._get_isa_tweak_auth(self._unsigned_token_session)
        with self.check(
            "Fake token prevents reading an ISA",
            participants=[self._dss.participant_id],
        ) as check:
            if get_fake_token.success:
                check.record_failed(
                    "Could read an ISA with a fake token",
                    Severity.High,
                    f"Attempting to read ISA {self._isa_id} with a fake token returned {get_fake_token.status_code}",
                    query_timestamps=[get_fake_token.query.request.timestamp],
                )

    def _wrong_auth_mutate(self):
        # Try to mutate an ISA with a read scope
        mutate_wrong_scope = self._put_isa_tweak_auth(
            utm_client=self._dss.client,
            scope_intent="read",
            isa_version=self._isa_version,
        )
        with self.check(
            "Read scope cannot mutate an ISA", participants=[self._dss.participant_id]
        ) as check:
            if mutate_wrong_scope.dss_query.success:
                check.record_failed(
                    "Read scope can mutate an ISA",
                    Severity.High,
                    f"Attempting to create ISA {self._isa_id} with read scope returned {mutate_wrong_scope.dss_query.status_code}",
                    query_timestamps=[
                        mutate_wrong_scope.dss_query.query.request.timestamp
                    ],
                )

        # Try to create an ISA with a missing token
        mutate_no_token = self._put_isa_tweak_auth(
            utm_client=self._no_token_session,
            scope_intent="write",
        )
        with self.check(
            "Missing token prevents mutating an ISA",
            participants=[self._dss.participant_id],
        ) as check:
            if mutate_no_token.dss_query.success:
                check.record_failed(
                    "Could mutate an ISA without a token",
                    Severity.High,
                    f"Attempting to create ISA {self._isa_id} with no token returned {mutate_no_token.dss_query.status_code}",
                    query_timestamps=[
                        mutate_no_token.dss_query.query.request.timestamp
                    ],
                )

        # Try to mutate an ISA with a fake token
        mutate_fake_token = self._put_isa_tweak_auth(
            utm_client=self._unsigned_token_session,
            scope_intent="write",
        )
        with self.check(
            "Fake token cannot mutate an ISA",
            participants=[self._dss.participant_id],
        ) as check:
            if mutate_fake_token.dss_query.success:
                check.record_failed(
                    "Could mutate an ISA with a fake token",
                    Severity.High,
                    f"Attempting to create ISA {self._isa_id} with a fake token returned {mutate_fake_token.dss_query.status_code}",
                    query_timestamps=[
                        mutate_fake_token.dss_query.query.request.timestamp
                    ],
                )

    def _wrong_auth_delete(self):
        # Try to delete an ISA with a read scope
        del_wrong_scope = self._del_isa_tweak_auth(
            utm_client=self._dss.client, scope_intent="read"
        )
        with self.check(
            "Read scope cannot delete an ISA", participants=[self._dss.participant_id]
        ) as check:
            if del_wrong_scope.dss_query.success:
                check.record_failed(
                    "Read scope can delete an ISA",
                    Severity.High,
                    f"Attempting to delete ISA {self._isa_id} with read scope returned {del_wrong_scope.dss_query.status_code}",
                    query_timestamps=[
                        del_wrong_scope.dss_query.query.request.timestamp
                    ],
                )

        if del_wrong_scope.dss_query.success:
            self._verify_notifications(del_wrong_scope.notifications)

        # Try to delete an ISA with a missing token
        del_no_token = self._del_isa_tweak_auth(
            utm_client=self._no_token_session,
            scope_intent="write",
        )
        with self.check(
            "Missing token prevents ISA deletion",
            participants=[self._dss.participant_id],
        ) as check:
            if del_no_token.dss_query.success:
                check.record_failed(
                    "Could mutate an ISA without a token",
                    Severity.High,
                    f"Attempting to create ISA {self._isa_id} with no token returned {del_no_token.dss_query.status_code}",
                    query_timestamps=[del_no_token.dss_query.query.request.timestamp],
                )

        if del_no_token.dss_query.success:
            self._verify_notifications(del_no_token.notifications)

        # Try to delete an ISA with a fake token
        del_fake_token = self._del_isa_tweak_auth(
            utm_client=self._unsigned_token_session,
            scope_intent="write",
        )
        with self.check(
            "Fake token cannot delete an ISA",
            participants=[self._dss.participant_id],
        ) as check:
            if del_fake_token.dss_query.success:
                check.record_failed(
                    "Could delete an ISA with a fake token",
                    Severity.High,
                    f"Attempting to create ISA {self._isa_id} with a fake token returned {del_fake_token.dss_query.status_code}",
                    query_timestamps=[del_fake_token.dss_query.query.request.timestamp],
                )

    def _wrong_auth_search(self):
        # confirm that a search with proper credentials returns a successful http code
        search_ok = self._search_isas_tweak_auth(
            utm_client=self._dss.client,
            area=self._isa_area,
            start_time=self._isa_start_time,
            end_time=self._isa_end_time,
        )

        with self.check(
            "Proper token is allowed to search for ISAs",
            participants=[self._dss.participant_id],
        ) as check:
            if not search_ok.success:
                check.record_failed(
                    "Search request failed although a valid token was used",
                    Severity.High,
                    f"Attempting to search ISAs with a valid token returned failure code: {search_ok.query.status_code}",
                    query_timestamps=[search_ok.query.request.timestamp],
                )

        # Search for ISAs with an invalid token
        search_wrong_token = self._search_isas_tweak_auth(
            utm_client=self._unsigned_token_session,
            area=self._isa_area,
            start_time=self._isa_start_time,
            end_time=self._isa_end_time,
        )

        with self.check(
            "Fake token cannot search for ISAs",
            participants=[self._dss.participant_id],
        ) as check:
            if search_wrong_token.success:
                check.record_failed(
                    "Search endpoint returned successfully without a token",
                    Severity.High,
                    f"Attempting to search ISAs with invalid token returned successful query: {search_wrong_token.query.status_code}",
                    query_timestamps=[search_wrong_token.query.request.timestamp],
                )

        # Search for ISAs with a missing token
        search_no_token = self._search_isas_tweak_auth(
            utm_client=self._no_token_session,
            area=self._isa_area,
            start_time=self._isa_start_time,
            end_time=self._isa_end_time,
        )

        with self.check(
            "Missing token cannot search for ISAs",
            participants=[self._dss.participant_id],
        ) as check:
            if search_no_token.success:
                check.record_failed(
                    "Search endpoint returned successfully without a token",
                    Severity.High,
                    f"Attempting to search ISAs with no token returned successful query: {search_no_token.query.status_code}",
                    query_timestamps=[search_no_token.query.request.timestamp],
                )

    def _delete_isa(self):
        del_isa_ok = self._del_isa_tweak_auth(self._dss.client, scope_intent="write")
        with self.check(
            "Correct token and scope can delete ISA",
            participants=[self._dss.participant_id],
        ) as check:
            if not del_isa_ok.dss_query.success:
                check.record_failed(
                    "Could not delete ISA with valid credentials",
                    Severity.High,
                    f"Attempting to delete ISA {self._isa_id} returned {del_isa_ok.dss_query.status_code}",
                    query_timestamps=[del_isa_ok.dss_query.query.request.timestamp],
                )

        self._verify_notifications(del_isa_ok.notifications)

    def _delete_isa_if_exists(self):
        fetched = rid_fetch.isa(
            self._isa_id,
            rid_version=self._dss.rid_version,
            session=self._dss.client,
            participant_id=self._dss.participant_id,
        )
        with self.check("Successful ISA query", [self._dss.participant_id]) as check:
            self.record_query(fetched.query)
            if not fetched.success and fetched.status_code != 404:
                check.record_failed(
                    "ISA information could not be retrieved",
                    Severity.High,
                    f"{self._dss.participant_id} DSS instance returned {fetched.status_code} when queried for ISA {self._isa_id}",
                    query_timestamps=[fetched.query.request.timestamp],
                )

        if fetched.success:
            deleted = mutate.delete_isa(
                self._isa_id,
                fetched.isa.version,
                self._dss.rid_version,
                self._dss.client,
                participant_id=self._dss.participant_id,
            )
            self.record_query(deleted.dss_query.query)
            for subscriber_id, notification in deleted.notifications.items():
                self.record_query(notification.query)
            with self.check(
                "Removed pre-existing ISA", [self._dss.participant_id]
            ) as check:
                if not deleted.dss_query.success:
                    check.record_failed(
                        "Could not delete pre-existing ISA",
                        Severity.High,
                        f"Attempting to delete ISA {self._isa_id} from the {self._dss.participant_id} DSS returned error {deleted.dss_query.status_code}",
                        query_timestamps=[deleted.dss_query.query.request.timestamp],
                    )
            self._verify_notifications(deleted.notifications)

    def _verify_notifications(self, notifications: Dict[str, ISAChangeNotification]):
        for subscriber_url, notification in notifications.items():
            pid = (
                notification.query.participant_id
                if "participant_id" in notification.query
                else None
            )
            with self.check("Notified subscriber", [pid] if pid else []) as check:
                if not notification.success:
                    check.record_failed(
                        "Could not notify ISA subscriber",
                        Severity.Medium,
                        f"Attempting to notify subscriber for ISA {self._isa_id} at {subscriber_url} resulted in {notification.status_code}",
                        query_timestamps=[notification.query.request.timestamp],
                    )

    def _put_isa_tweak_auth(
        self,
        utm_client: infrastructure.UTMClientSession,
        isa_version: Optional[str] = None,
        scope_intent: str = "read",
    ) -> ISAChange:
        """A local version of mutate.rid.put_isa that lets us control authentication parameters"""
        mutation = "create" if isa_version is None else "update"

        query_scope = self._query_scope_for_auth_params(utm_client, scope_intent)

        if self._dss.rid_version == RIDVersion.f3411_19:
            body = {
                "extents": rid_v1.make_volume_4d(
                    self._isa_area,
                    self._isa.altitude_min,
                    self._isa.altitude_max,
                    self._isa_start_time,
                    self._isa_end_time,
                ),
                "flights_url": self._isa.base_url
                + v19.api.OPERATIONS[v19.api.OperationID.SearchFlights].path,
            }
            if isa_version is None:
                op = v19.api.OPERATIONS[
                    v19.api.OperationID.CreateIdentificationServiceArea
                ]
                url = op.path.format(id=self._isa_id)
            else:
                op = v19.api.OPERATIONS[
                    v19.api.OperationID.UpdateIdentificationServiceArea
                ]
                url = op.path.format(id=self._isa_id, version=isa_version)
            dss_response = ChangedISA(
                mutation=mutation,
                v19_query=fetch.query_and_describe(
                    utm_client,
                    op.verb,
                    url,
                    json=body,
                    participant_id=self._dss.participant_id,
                    **({} if query_scope is None else {"scope": query_scope}),
                ),
            )
        elif self._dss.rid_version == RIDVersion.f3411_22a:
            body = {
                "extents": rid_v2.make_volume_4d(
                    self._isa_area,
                    self._isa.altitude_min,
                    self._isa.altitude_max,
                    self._isa_start_time,
                    self._isa_end_time,
                ),
                "uss_base_url": self._isa.base_url,
            }
            if isa_version is None:
                op = v22a.api.OPERATIONS[
                    v22a.api.OperationID.CreateIdentificationServiceArea
                ]
                url = op.path.format(id=self._isa_id)
            else:
                op = v22a.api.OPERATIONS[
                    v22a.api.OperationID.UpdateIdentificationServiceArea
                ]
                url = op.path.format(id=self._isa_id, version=isa_version)
            dss_response = ChangedISA(
                mutation=mutation,
                v22a_query=fetch.query_and_describe(
                    utm_client,
                    op.verb,
                    url,
                    json=body,
                    participant_id=self._dss.participant_id,
                    **({} if query_scope is None else {"scope": query_scope}),
                ),
            )

        if dss_response.success:
            isa = dss_response.isa
            notifications = {
                sub.url: sub.notify(isa.id, utm_client, isa)
                for sub in dss_response.subscribers
            }
        else:
            notifications = {}

        self.record_query(dss_response.query)

        return ISAChange(dss_query=dss_response, notifications=notifications)

    def _get_isa_tweak_auth(self, utm_client: infrastructure.UTMClientSession):
        """A local version of fetch.rid.isa that lets us control authentication parameters"""
        if self._dss.rid_version == RIDVersion.f3411_19:
            op = v19.api.OPERATIONS[v19.api.OperationID.GetIdentificationServiceArea]
            url = f"{self._dss.base_url}{op.path}".replace("{id}", self._isa_id)
            return FetchedISA(
                v19_query=fetch.query_and_describe(
                    utm_client,
                    op.verb,
                    url,
                    participant_id=self._dss.participant_id,
                    **(
                        {}
                        if utm_client.auth_adapter is None
                        else {"scope": v19.constants.Scope.Read}
                    ),
                )
            )
        elif self._dss.rid_version == RIDVersion.f3411_22a:
            op = v22a.api.OPERATIONS[v22a.api.OperationID.GetIdentificationServiceArea]
            url = f"{self._dss.base_url}{op.path}".replace("{id}", self._isa_id)
            return FetchedISA(
                v22a_query=fetch.query_and_describe(
                    utm_client,
                    op.verb,
                    url,
                    participant_id=self._dss.participant_id,
                    **(
                        {}
                        if utm_client.auth_adapter is None
                        else {"scope": v22a.constants.Scope.DisplayProvider}
                    ),
                )
            )

        else:
            raise NotImplementedError(
                f"Cannot query DSS for ISA using RID version {self._dss.rid_version}"
            )

    def _del_isa_tweak_auth(
        self,
        utm_client: infrastructure.UTMClientSession,
        scope_intent: str = "read",
    ) -> ISAChange:
        """A local version of mutate.rid.delete_isa that lets us control authentication parameters"""
        query_scope = self._query_scope_for_auth_params(utm_client, scope_intent)

        if self._dss.rid_version == RIDVersion.f3411_19:
            op = v19.api.OPERATIONS[v19.api.OperationID.DeleteIdentificationServiceArea]
            url = op.path.format(id=self._isa_id, version=self._isa_version)
            dss_response = ChangedISA(
                mutation="delete",
                v19_query=fetch.query_and_describe(
                    utm_client,
                    op.verb,
                    url,
                    participant_id=self._dss.participant_id,
                    **({} if query_scope is None else {"scope": query_scope}),
                ),
            )
        elif self._dss.rid_version == RIDVersion.f3411_22a:
            op = v22a.api.OPERATIONS[
                v22a.api.OperationID.DeleteIdentificationServiceArea
            ]
            url = op.path.format(id=self._isa_id, version=self._isa_version)
            dss_response = ChangedISA(
                mutation="delete",
                v22a_query=fetch.query_and_describe(
                    utm_client,
                    op.verb,
                    url,
                    participant_id=self._dss.participant_id,
                    **({} if query_scope is None else {"scope": query_scope}),
                ),
            )
        else:
            raise NotImplementedError(
                f"Cannot delete ISA using RID version {self._dss.rid_version}"
            )

        if dss_response.success:
            isa = dss_response.isa
            notifications = {
                sub.url: sub.notify(isa.id, utm_client)
                for sub in dss_response.subscribers
            }
        else:
            notifications = {}

        self.record_query(dss_response.query)
        for notification_query in notifications.values():
            self.record_query(notification_query.query)

        return ISAChange(dss_query=dss_response, notifications=notifications)

    def _search_isas_tweak_auth(
        self,
        utm_client: infrastructure.UTMClientSession,
        area: List[s2sphere.LatLng],
        start_time: Optional[datetime.datetime],
        end_time: Optional[datetime.datetime],
    ) -> FetchedISAs:

        url_time_params = ""
        if start_time is not None:
            url_time_params += (
                f"&earliest_time={self._dss.rid_version.format_time(start_time)}"
            )
        if end_time is not None:
            url_time_params += (
                f"&latest_time={self._dss.rid_version.format_time(end_time)}"
            )

        query_scope = self._query_scope_for_auth_params(utm_client, "read")

        """A local version of fetch.rid.isas that lets us control authentication parameters"""
        if self._dss.rid_version == RIDVersion.f3411_19:
            op = v19.api.OPERATIONS[
                v19.api.OperationID.SearchIdentificationServiceAreas
            ]
            area_str = rid_v1.geo_polygon_string_from_s2(area)
            url = f"{self._dss.base_url}{op.path}?area={area_str}{url_time_params}"
            response = FetchedISAs(
                v19_query=fetch.query_and_describe(
                    utm_client,
                    op.verb,
                    url,
                    participant_id=self._dss.participant_id,
                    **({} if query_scope is None else {"scope": query_scope}),
                )
            )
        elif self._dss.rid_version == RIDVersion.f3411_22a:
            op = v22a.api.OPERATIONS[
                v22a.api.OperationID.SearchIdentificationServiceAreas
            ]
            area_str = rid_v2.geo_polygon_string_from_s2(area)
            url = f"{self._dss.base_url}{op.path}?area={area_str}{url_time_params}"
            response = FetchedISAs(
                v22a_query=fetch.query_and_describe(
                    utm_client,
                    op.verb,
                    url,
                    participant_id=self._dss.participant_id,
                    **({} if query_scope is None else {"scope": query_scope}),
                )
            )
        else:
            raise NotImplementedError(
                f"Cannot query DSS for ISAs using RID version {self._dss.rid_version}"
            )

        self.record_query(response.query)
        return response

    def _query_scope_for_auth_params(
        self, utm_client: infrastructure.UTMClientSession, scope_intent: str
    ) -> Optional[str]:

        if utm_client.auth_adapter is not None:
            if self._dss.rid_version == RIDVersion.f3411_19:
                if scope_intent == "read":
                    return v19.constants.Scope.Read
                else:
                    return v19.constants.Scope.Write
            elif self._dss.rid_version == RIDVersion.f3411_22a:
                # There are no explicit 'read' or 'write' scopes in v22a,
                # instead the scopes represent what kind of provider is accessing the DSS.
                # DisplayProviders can only read ISAs and create subscriptions
                # while ServiceProviders can do everything.
                if scope_intent == "read":
                    return v22a.constants.Scope.DisplayProvider
                else:
                    return v22a.constants.Scope.ServiceProvider
            else:
                raise NotImplementedError(
                    f"Cannot upsert ISA using RID version {self._dss.rid_version}"
                )

        return None

    def cleanup(self):
        self.begin_cleanup()

        self._delete_isa_if_exists()

        self.end_cleanup()
