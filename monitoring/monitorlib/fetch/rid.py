from __future__ import annotations
import arrow
import datetime
from typing import Dict, List, Optional, Any, Union

from implicitdict import ImplicitDict
import s2sphere
from uas_standards.astm.f3411 import v19, v22a
import uas_standards.astm.f3411.v19.api
import uas_standards.astm.f3411.v19.constants
import uas_standards.astm.f3411.v22a.api
import uas_standards.astm.f3411.v22a.constants
import yaml
from yaml.representer import Representer

from monitoring.monitorlib import fetch, infrastructure, rid_v1
from monitoring.monitorlib.fetch import Query
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.monitorlib.rid_common import RIDVersion


class RIDQuery(ImplicitDict):
    v19_query: Optional[Query] = None
    v22a_query: Optional[Query] = None

    @property
    def rid_version(self) -> RIDVersion:
        if self.v19_query is not None:
            return RIDVersion.f3411_19
        elif self.v22a_query is not None:
            return RIDVersion.f3411_22a
        else:
            raise ValueError(f"No valid query was populated in {type(self).__name__}")

    @property
    def query(self) -> Query:
        if self.rid_version == RIDVersion.f3411_19:
            return self.v19_query
        elif self.rid_version == RIDVersion.f3411_22a:
            return self.v22a_query
        else:
            raise NotImplementedError(
                f"Cannot retrieve query using RID version {self.rid_version}"
            )

    @property
    def status_code(self):
        return self.query.status_code


class ISA(ImplicitDict):
    """Version-independent representation of a F3411 identification service area."""

    v19: Optional[v19.api.IdentificationServiceArea]
    v22a: Optional[v22a.api.IdentificationServiceArea]

    @property
    def rid_version(self) -> RIDVersion:
        if self.v19 is not None:
            return RIDVersion.f3411_19
        elif self.v22a is not None:
            return RIDVersion.f3411_22a
        else:
            raise ValueError("No valid representation was specified for ISA")

    @property
    def raw(
        self,
    ) -> Union[v19.api.IdentificationServiceArea, v22a.api.IdentificationServiceArea]:
        if self.rid_version == RIDVersion.f3411_19:
            return self.v19
        elif self.rid_version == RIDVersion.f3411_22a:
            return self.v22a
        else:
            raise NotImplementedError(
                f"Cannot retrieve raw ISA using RID version {self.rid_version}"
            )

    @property
    def flights_url(self) -> str:
        if self.rid_version == RIDVersion.f3411_19:
            return self.v19.flights_url
        elif self.rid_version == RIDVersion.f3411_22a:
            flights_path = v22a.api.OPERATIONS[v22a.api.OperationID.SearchFlights].path
            return self.v22a.uss_base_url + flights_path
        else:
            raise NotImplementedError(
                f"Cannot retrieve ISA flights URLs using RID version {self.rid_version}"
            )

    @property
    def owner(self) -> str:
        return self.raw.owner

    @property
    def id(self) -> str:
        return self.raw.id


class FetchedISAs(RIDQuery):
    """Version-independent representation of a list of F3411 identification service areas."""

    @property
    def _v19_response(
        self,
    ) -> Optional[v19.api.SearchIdentificationServiceAreasResponse]:
        try:
            return ImplicitDict.parse(
                self.v19_query.response.json,
                v19.api.SearchIdentificationServiceAreasResponse,
            )
        except ValueError:
            return None

    @property
    def _v22a_response(
        self,
    ) -> Optional[v22a.api.SearchIdentificationServiceAreasResponse]:
        try:
            return ImplicitDict.parse(
                self.v22a_query.response.json,
                v22a.api.SearchIdentificationServiceAreasResponse,
            )
        except ValueError:
            return None

    @property
    def error(self) -> Optional[str]:
        # Overall errors
        if self.status_code != 200:
            return f"Failed to search ISAs in DSS ({self.status_code})"

        if self.query.response.json is None:
            return "DSS response to search ISAs did not contain valid JSON"

        if self.rid_version == RIDVersion.f3411_19:
            if self._v19_response is None:
                try:
                    ImplicitDict.parse(
                        self.v19_query.response.json,
                        v19.api.SearchIdentificationServiceAreasResponse,
                    )
                    return "Unknown error with F3411-19 SearchIdentificationServiceAreasResponse"
                except ValueError as e:
                    return f"Error parsing F3411-19 DSS SearchIdentificationServiceAreasResponse: {str(e)}"

        if self.rid_version == RIDVersion.f3411_22a:
            if self._v22a_response is None:
                try:
                    ImplicitDict.parse(
                        self.v22a_query.response.json,
                        v22a.api.SearchIdentificationServiceAreasResponse,
                    )
                    return "Unknown error with F3411-22a SearchIdentificationServiceAreasResponse"
                except ValueError as e:
                    return f"Error parsing F3411-22a DSS SearchIdentificationServiceAreasResponse: {str(e)}"

        return None

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def isas(self) -> Dict[str, ISA]:
        if not self.success:
            return {}
        if self.rid_version == RIDVersion.f3411_19:
            return {isa.id: ISA(v19=isa) for isa in self._v19_response.service_areas}
        elif self.rid_version == RIDVersion.f3411_22a:
            return {isa.id: ISA(v22a=isa) for isa in self._v22a_response.service_areas}
        else:
            raise NotImplementedError(
                f"Cannot retrieve ISAs using RID version {self.rid_version}"
            )

    @property
    def flights_urls(self) -> Dict[str, str]:
        """Returns map of flights URL to owning USS"""
        if not self.success:
            return {}
        return {isa.flights_url: isa.owner for _, isa in self.isas.items()}

    def has_different_content_than(self, other: Any) -> bool:
        if not isinstance(other, FetchedISAs):
            return True
        if self.error != other.error:
            return True
        if self.rid_version != other.rid_version:
            return True

        if self.rid_version == RIDVersion.f3411_19:
            return self._v19_response != other._v19_response
        elif self.rid_version == RIDVersion.f3411_22a:
            return self._v22_response != other._v22_response
        else:
            raise NotImplementedError(
                f"Cannot compare ISAs using RID version {self.rid_version}"
            )


yaml.add_representer(FetchedISAs, Representer.represent_dict)


def isas(
    box: s2sphere.LatLngRect,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    rid_version: RIDVersion,
    session: UTMClientSession,
    dss_base_url: str = "",
) -> FetchedISAs:
    t0 = rid_version.format_time(start_time)
    t1 = rid_version.format_time(end_time)
    if rid_version == RIDVersion.f3411_19:
        op = v19.api.OPERATIONS[v19.api.OperationID.SearchIdentificationServiceAreas]
        area = rid_v1.geo_polygon_string(rid_v1.vertices_from_latlng_rect(box))
        url = f"{dss_base_url}{op.path}?area={area}&earliest_time={t0}&latest_time={t1}"
        return FetchedISAs(
            v19_query=fetch.query_and_describe(
                session, op.verb, url, scope=v19.constants.Scope.Read
            )
        )
    elif rid_version == RIDVersion.f3411_22a:
        op = v22a.api.OPERATIONS[v22a.api.OperationID.SearchIdentificationServiceAreas]
        area = rid_v1.geo_polygon_string(rid_v1.vertices_from_latlng_rect(box))
        url = f"{dss_base_url}{op.path}?area={area}&earliest_time={t0}&latest_time={t1}"
        return FetchedISAs(
            v22a_query=fetch.query_and_describe(
                session, op.verb, url, scope=v22a.constants.Scope.DisplayProvider
            )
        )
    else:
        raise NotImplementedError(
            f"Cannot query DSS for ISA list using RID version {rid_version}"
        )


class Flight(ImplicitDict):
    """Version-independent representation of a F3411 flight."""

    v19: Optional[v19.api.RIDFlight]
    v22a: Optional[v22a.api.RIDFlight]

    @property
    def rid_version(self) -> RIDVersion:
        if self.v19 is not None:
            return RIDVersion.f3411_19
        elif self.v22a is not None:
            return RIDVersion.f3411_22a
        else:
            raise ValueError("No valid representation was specified for flight")

    @property
    def raw(
        self,
    ) -> Union[v19.api.RIDFlight, v22a.api.RIDFlight]:
        if self.rid_version == RIDVersion.f3411_19:
            return self.v19
        elif self.rid_version == RIDVersion.f3411_22a:
            return self.v22a
        else:
            raise NotImplementedError(
                f"Cannot retrieve raw flight using RID version {self.rid_version}"
            )

    @property
    def id(self) -> str:
        return self.raw.id

    def as_v19(self) -> v19.api.RIDFlight:
        if self.v19 is not None:
            return self.v19
        else:
            raise NotImplementedError(f"Conversion to F3411-19 RIDFlight has not yet been implemented for RID version {self.rid_version}")


class FetchedUSSFlights(RIDQuery):
    """Version-independent representation of a list of flights reported by a USS."""

    @property
    def _v19_response(
        self,
    ) -> Optional[v19.api.GetFlightsResponse]:
        try:
            return ImplicitDict.parse(
                self.v19_query.response.json,
                v19.api.GetFlightsResponse,
            )
        except ValueError:
            return None

    @property
    def _v22a_response(
        self,
    ) -> Optional[v22a.api.GetFlightsResponse]:
        try:
            return ImplicitDict.parse(
                self.v22a_query.response.json,
                v22a.api.GetFlightsResponse,
            )
        except ValueError:
            return None

    @property
    def success(self) -> bool:
        return not self.errors

    @property
    def errors(self) -> List[str]:
        if self.status_code != 200:
            return ["Failed to get flights ({})".format(self.status_code)]
        if self.query.response.json is None:
            return ["Flights response did not include valid JSON"]

        if self.rid_version == RIDVersion.f3411_19:
            if self._v19_response is None:
                try:
                    ImplicitDict.parse(
                        self.v19_query.response.json,
                        v19.api.GetFlightsResponse,
                    )
                    return ["Unknown error with F3411-19 GetFlightsResponse"]
                except ValueError as e:
                    return [f"Error parsing F3411-19 USS GetFlightsResponse: {str(e)}"]

        if self.rid_version == RIDVersion.f3411_22a:
            if self._v22a_response is None:
                try:
                    ImplicitDict.parse(
                        self.v22a_query.response.json,
                        v22a.api.GetFlightsResponse,
                    )
                    return ["Unknown error with F3411-22a GetFlightsResponse"]
                except ValueError as e:
                    return [f"Error parsing F3411-22a USS GetFlightsResponse: {str(e)}"]

        return []

    @property
    def flights(self) -> List[Flight]:
        if not self.success:
            return []
        if self.rid_version == RIDVersion.f3411_19:
            return [Flight(v19=f) for f in self._v19_response.flights]
        elif self.rid_version == RIDVersion.f3411_22a:
            return [Flight(v22a=f) for f in self._v22a_response.flights]
        else:
            raise NotImplementedError(
                f"Cannot retrieve flights using RID version {self.rid_version}"
            )


yaml.add_representer(FetchedUSSFlights, Representer.represent_dict)


def uss_flights(
    flights_url: str,
    area: s2sphere.LatLngRect,
    include_recent_positions: bool,
    rid_version: RIDVersion,
    session: UTMClientSession,
) -> FetchedUSSFlights:
    if rid_version == RIDVersion.f3411_19:
        query = fetch.query_and_describe(
            session,
            "GET",
            flights_url,
            params={
                "view": "{},{},{},{}".format(
                    area.lat_lo().degrees,
                    area.lng_lo().degrees,
                    area.lat_hi().degrees,
                    area.lng_hi().degrees,
                ),
                "include_recent_positions": "true"
                if include_recent_positions
                else "false",
            },
            scope=v19.constants.Scope.Read,
        )
        return FetchedUSSFlights(v19_query=query)
    elif rid_version == RIDVersion.f3411_22a:
        params = {
            "view": "{},{},{},{}".format(
                area.lat_lo().degrees,
                area.lng_lo().degrees,
                area.lat_hi().degrees,
                area.lng_hi().degrees,
            ),
        }
        if include_recent_positions:
            params["recent_positions_duration"] = "60"
        query = fetch.query_and_describe(
            session,
            "GET",
            flights_url,
            params=params,
            scope=v22a.constants.Scope.DisplayProvider,
        )
        return FetchedUSSFlights(v22a_query=query)
    else:
        raise NotImplementedError(
            f"Cannot query USS for flights using RID version {rid_version}"
        )


class FlightDetails(ImplicitDict):
    """Version-independent representation of details for a F3411 flight."""

    v19: Optional[v19.api.RIDFlightDetails]
    v22a: Optional[v22a.api.RIDFlightDetails]

    @property
    def rid_version(self) -> RIDVersion:
        if self.v19 is not None:
            return RIDVersion.f3411_19
        elif self.v22a is not None:
            return RIDVersion.f3411_22a
        else:
            raise ValueError("No valid representation was specified for flight details")

    @property
    def raw(
        self,
    ) -> Union[v19.api.RIDFlightDetails, v22a.api.RIDFlightDetails]:
        if self.rid_version == RIDVersion.f3411_19:
            return self.v19
        elif self.rid_version == RIDVersion.f3411_22a:
            return self.v22a
        else:
            raise NotImplementedError(
                f"Cannot retrieve raw flight details using RID version {self.rid_version}"
            )

    @property
    def id(self) -> str:
        return self.raw.id


class FetchedUSSFlightDetails(RIDQuery):
    """Version-independent representation of the details of a flight reported by a USS."""

    requested_id: str

    @property
    def _v19_response(
        self,
    ) -> Optional[v19.api.GetFlightDetailsResponse]:
        try:
            return ImplicitDict.parse(
                self.v19_query.response.json,
                v19.api.GetFlightDetailsResponse,
            )
        except ValueError:
            return None

    @property
    def _v22a_response(
        self,
    ) -> Optional[v22a.api.GetFlightDetailsResponse]:
        try:
            return ImplicitDict.parse(
                self.v22a_query.response.json,
                v22a.api.GetFlightDetailsResponse,
            )
        except ValueError:
            return None

    @property
    def success(self) -> bool:
        return not self.errors

    @property
    def errors(self) -> List[str]:
        if self.status_code != 200:
            return ["Failed to get flight details ({})".format(self.status_code)]
        if self.query.response.json is None:
            return ["Flight details response did not include valid JSON"]

        if self.rid_version == RIDVersion.f3411_19:
            if self._v19_response is None:
                try:
                    ImplicitDict.parse(
                        self.v19_query.response.json,
                        v19.api.GetFlightDetailsResponse,
                    )
                    return ["Unknown error with F3411-19 GetFlightDetailsResponse"]
                except ValueError as e:
                    return [
                        f"Error parsing F3411-19 USS GetFlightDetailsResponse: {str(e)}"
                    ]

        if self.rid_version == RIDVersion.f3411_22a:
            if self._v22a_response is None:
                try:
                    ImplicitDict.parse(
                        self.v22a_query.response.json,
                        v22a.api.GetFlightDetailsResponse,
                    )
                    return ["Unknown error with F3411-22a GetFlightDetailsResponse"]
                except ValueError as e:
                    return [
                        f"Error parsing F3411-22a USS GetFlightDetailsResponse: {str(e)}"
                    ]

        return []

    @property
    def details(self) -> Optional[FlightDetails]:
        if not self.success:
            return None
        if self.rid_version == RIDVersion.f3411_19:
            return FlightDetails(v19=self._v19_response.details)
        elif self.rid_version == RIDVersion.f3411_22a:
            return FlightDetails(v22a=self._v22a_response.details)
        else:
            raise NotImplementedError(
                f"Cannot retrieve flight details using RID version {self.rid_version}"
            )


yaml.add_representer(FetchedUSSFlightDetails, Representer.represent_dict)


def flight_details(
    flights_url: str,
    flight_id: str,
    enhanced_details: bool,
    rid_version: RIDVersion,
    session: UTMClientSession,
) -> FetchedUSSFlightDetails:
    url = f"{flights_url}/{flight_id}/details"
    if rid_version == RIDVersion.f3411_19:
        kwargs = {}
        if enhanced_details:
            kwargs["params"] = {"enhanced": "true"}
            kwargs["scope"] = (
                v19.constants.Scope.Read + " " + rid_v1.UPP2_SCOPE_ENHANCED_DETAILS
            )
        else:
            kwargs["scope"] = v19.constants.Scope.Read
        query = fetch.query_and_describe(
            session,
            "GET",
            url,
            **kwargs,
        )
        return FetchedUSSFlightDetails(v19_query=query, requested_id=flight_id)
    elif rid_version == RIDVersion.f3411_22a:
        query = fetch.query_and_describe(
            session, "GET", flights_url, scope=v22a.constants.Scope.DisplayProvider
        )
        return FetchedUSSFlightDetails(v22a_query=query, requested_id=flight_id)
    else:
        raise NotImplementedError(
            f"Cannot query USS for flight details using RID version {rid_version}"
        )


class FetchedFlights(ImplicitDict):
    dss_isa_query: FetchedISAs
    uss_flight_queries: Dict[str, FetchedUSSFlights]
    uss_flight_details_queries: Dict[str, FetchedUSSFlightDetails]

    @property
    def success(self):
        return not self.errors

    @property
    def errors(self) -> List[str]:
        if not self.dss_isa_query.success:
            return ["Failed to obtain ISAs: " + self.dss_isa_query.error]
        result = []
        for flights in self.uss_flight_queries.values():
            result.extend(flights.errors)
        for uss_details in self.uss_flight_details_queries.values():
            result.extend(uss_details.errors)
        return result


yaml.add_representer(FetchedFlights, Representer.represent_dict)


def all_flights(
    area: s2sphere.LatLngRect,
    include_recent_positions: bool,
    get_details: bool,
    rid_version: RIDVersion,
    session: UTMClientSession,
    dss_base_url: str = "",
    enhanced_details: bool = False,
) -> FetchedFlights:
    t = datetime.datetime.utcnow()
    isa_list = isas(area, t, t, rid_version, session, dss_base_url)

    uss_flight_queries: Dict[str, FetchedUSSFlights] = {}
    uss_flight_details_queries: Dict[str, FetchedUSSFlightDetails] = {}
    for flights_url in isa_list.flight_urls:
        flights_for_url = uss_flights(
            flights_url, area, include_recent_positions, rid_version, session
        )
        uss_flight_queries[flights_url] = flights_for_url

        if get_details and flights_for_url.success:
            for flight in flights_for_url.flights:
                details = flight_details(
                    flights_url, flight.id, enhanced_details, rid_version, session
                )
                uss_flight_details_queries[flight.id] = details

    return FetchedFlights(
        dss_isa_query=isa_list,
        uss_flight_queries=uss_flight_queries,
        uss_flight_details_querie=uss_flight_details_queries,
    )


class FetchedSubscription(fetch.Query):
    """Wrapper to interpret a DSS Subscription query as a Subscription."""

    @property
    def success(self) -> bool:
        return not self.errors

    @property
    def errors(self) -> List[str]:
        if self.status_code == 404:
            return []
        if self.status_code != 200:
            return ["Request to get Subscription failed ({})".format(self.status_code)]
        if self.json_result is None:
            return ["Request to get Subscription did not return valid JSON"]
        if not self._subscription.valid:
            return ["Invalid Subscription data"]
        return []

    @property
    def _subscription(self) -> rid_v1.Subscription:
        return rid_v1.Subscription(self.json_result.get("subscription", {}))

    @property
    def subscription(self) -> Optional[rid_v1.Subscription]:
        if not self.success or self.status_code == 404:
            return None
        else:
            return self._subscription


yaml.add_representer(FetchedSubscription, Representer.represent_dict)


def subscription(
    utm_client: infrastructure.UTMClientSession, subscription_id: str
) -> FetchedSubscription:
    url = "/v1/dss/subscriptions/{}".format(subscription_id)
    result = fetch.query_and_describe(utm_client, "GET", url, scope=rid_v1.SCOPE_READ)
    return FetchedSubscription(result)
