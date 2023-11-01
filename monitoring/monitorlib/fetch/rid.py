from __future__ import annotations

import datetime
from typing import Dict, List, Optional, Any, Union

import s2sphere
import uas_standards.astm.f3411.v19.api
import uas_standards.astm.f3411.v19.constants
import uas_standards.astm.f3411.v22a.api
import uas_standards.astm.f3411.v22a.constants
import yaml
from implicitdict import ImplicitDict, StringBasedDateTime
from uas_standards.astm.f3411 import v19, v22a
from uas_standards.astm.f3411.v22a.api import RIDHeight
from yaml.representer import Representer

from monitoring.monitorlib import fetch, rid_v1, rid_v2, geo
from monitoring.monitorlib.fetch import Query, QueryType
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.monitorlib.rid import RIDVersion


class ISA(ImplicitDict):
    """Version-independent representation of a F3411 identification service area."""

    v19_value: Optional[v19.api.IdentificationServiceArea] = None
    v22a_value: Optional[v22a.api.IdentificationServiceArea] = None

    @property
    def rid_version(self) -> RIDVersion:
        if self.v19_value is not None:
            return RIDVersion.f3411_19
        elif self.v22a_value is not None:
            return RIDVersion.f3411_22a
        else:
            raise ValueError("No valid representation was specified for ISA")

    @property
    def raw(
        self,
    ) -> Union[v19.api.IdentificationServiceArea, v22a.api.IdentificationServiceArea]:
        if self.rid_version == RIDVersion.f3411_19:
            return self.v19_value
        elif self.rid_version == RIDVersion.f3411_22a:
            return self.v22a_value
        else:
            raise NotImplementedError(
                f"Cannot retrieve raw ISA using RID version {self.rid_version}"
            )

    def as_v19(self) -> v19.api.IdentificationServiceArea:
        if self.rid_version == RIDVersion.f3411_19:
            return self.v19_value
        elif self.rid_version == RIDVersion.f3411_22a:
            return v19.api.IdentificationServiceArea(
                flights_url=self.flights_url,
                owner=self.v22a_value.owner,
                time_start=self.v22a_value.time_start.value,
                time_end=self.v22a_value.time_end.value,
                version=self.v22a_value.version,
                id=self.v22a_value.id,
            )
        else:
            raise NotImplementedError(
                f"Cannot generate v19 representation of ISA using RID version {self.rid_version}"
            )

    def as_v22a(self) -> v22a.api.IdentificationServiceArea:
        if self.rid_version == RIDVersion.f3411_22a:
            return self.v22a_value
        else:
            raise NotImplementedError(
                f"Cannot generate v22a representation of ISA using RID version {self.rid_version}"
            )

    @property
    def flights_url(self) -> str:
        if self.rid_version == RIDVersion.f3411_19:
            return self.v19_value.flights_url
        elif self.rid_version == RIDVersion.f3411_22a:
            flights_path = v22a.api.OPERATIONS[v22a.api.OperationID.SearchFlights].path
            return self.v22a_value.uss_base_url + flights_path
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

    @property
    def version(self) -> str:
        return self.raw.version

    @property
    def time_start(self) -> datetime.datetime:
        if self.rid_version == RIDVersion.f3411_19:
            return self.v19_value.time_start.datetime
        elif self.rid_version == RIDVersion.f3411_22a:
            return self.v22a_value.time_start.value.datetime
        else:
            raise NotImplementedError(
                f"Cannot retrieve time_start using RID version {self.rid_version}"
            )

    @property
    def time_end(self) -> datetime.datetime:
        if self.rid_version == RIDVersion.f3411_19:
            return self.v19_value.time_end.datetime
        elif self.rid_version == RIDVersion.f3411_22a:
            return self.v22a_value.time_end.value.datetime
        else:
            raise NotImplementedError(
                f"Cannot retrieve time_end using RID version {self.rid_version}"
            )

    def query_flights(
        self,
        session: UTMClientSession,
        area: s2sphere.LatLngRect,
        include_recent_positions: bool = True,
        participant_id: Optional[str] = None,
    ) -> FetchedUSSFlights:
        return uss_flights(
            self.flights_url,
            area,
            include_recent_positions,
            self.rid_version,
            session,
            participant_id=participant_id,
        )


class Position(ImplicitDict):
    """Version-independent representation of a 3D position."""

    lat: float
    """Degrees north of equator."""

    lng: float
    """Degrees east of prime meridian."""

    alt: float
    """Meters above the WGS84 reference ellipsoid."""

    time: datetime.datetime
    """Timestamp for the position."""

    height: Optional[RIDHeight]

    @staticmethod
    def from_v19_rid_aircraft_position(
        p: v19.api.RIDAircraftPosition, t: v19.api.StringBasedDateTime
    ) -> Position:
        return Position(lat=p.lat, lng=p.lng, alt=p.alt, time=t.datetime, height=None)

    @staticmethod
    def from_v22a_rid_aircraft_position(
        p: v22a.api.RIDAircraftPosition, t: v22a.api.StringBasedDateTime
    ) -> Position:
        return Position(
            lat=p.lat, lng=p.lng, alt=p.alt, time=t.datetime, height=p.get("height")
        )


class Flight(ImplicitDict):
    """Version-independent representation of a F3411 flight."""

    v19_value: Optional[v19.api.RIDFlight] = None
    v22a_value: Optional[v22a.api.RIDFlight] = None

    @property
    def rid_version(self) -> RIDVersion:
        if self.v19_value is not None:
            return RIDVersion.f3411_19
        elif self.v22a_value is not None:
            return RIDVersion.f3411_22a
        else:
            raise ValueError("No valid representation was specified for flight")

    @property
    def raw(
        self,
    ) -> Union[v19.api.RIDFlight, v22a.api.RIDFlight]:
        if self.rid_version == RIDVersion.f3411_19:
            return self.v19_value
        elif self.rid_version == RIDVersion.f3411_22a:
            return self.v22a_value
        else:
            raise NotImplementedError(
                f"Cannot retrieve raw flight using RID version {self.rid_version}"
            )

    @property
    def id(self) -> str:
        return self.raw.id

    @property
    def most_recent_position(
        self,
    ) -> Optional[Position]:
        if "current_state" in self.raw and self.raw.current_state:
            if self.rid_version == RIDVersion.f3411_19:
                return Position.from_v19_rid_aircraft_position(
                    self.v19_value.current_state.position,
                    self.v19_value.current_state.timestamp,
                )
            elif self.rid_version == RIDVersion.f3411_22a:
                return Position.from_v22a_rid_aircraft_position(
                    self.v22a_value.current_state.position,
                    self.v22a_value.current_state.timestamp.value,
                )
            else:
                raise NotImplementedError(
                    f"Cannot retrieve most_recent_position using RID version {self.rid_version}"
                )
        else:
            return None

    @property
    def recent_positions(self) -> List[Position]:
        if self.rid_version == RIDVersion.f3411_19:
            return [
                Position.from_v19_rid_aircraft_position(p.position, p.time)
                for p in self.v19_value.recent_positions
            ]
        elif self.rid_version == RIDVersion.f3411_22a:
            return [
                Position.from_v22a_rid_aircraft_position(p.position, p.time.value)
                for p in self.v22a_value.recent_positions
            ]
        else:
            raise NotImplementedError(
                f"Cannot retrieve recent_positions using RID version {self.rid_version}"
            )

    @property
    def operational_status(self) -> Optional[str]:
        if self.rid_version == RIDVersion.f3411_19:
            if not self.v19_value.has_field_with_value(
                "current_state"
            ) or not self.v19_value.current_state.has_field_with_value(
                "operational_status"
            ):
                return None
            return self.v19_value.current_state.operational_status
        elif self.rid_version == RIDVersion.f3411_22a:
            if not self.v22a_value.has_field_with_value(
                "current_state"
            ) or not self.v22a_value.current_state.has_field_with_value(
                "operational_status"
            ):
                return None
            return self.v22a_value.current_state.operational_status
        else:
            raise NotImplementedError(
                f"Cannot retrieve operational_status using RID version {self.rid_version}"
            )

    @property
    def track(self) -> Optional[float]:
        if self.rid_version == RIDVersion.f3411_19:
            if not self.v19_value.has_field_with_value(
                "current_state"
            ) or not self.v19_value.current_state.has_field_with_value("track"):
                return None
            return self.v19_value.current_state.track
        elif self.rid_version == RIDVersion.f3411_22a:
            if not self.v22a_value.has_field_with_value(
                "current_state"
            ) or not self.v22a_value.current_state.has_field_with_value("track"):
                return None
            return self.v22a_value.current_state.track
        else:
            raise NotImplementedError(
                f"Cannot retrieve track using RID version {self.rid_version}"
            )

    @property
    def speed(self) -> Optional[float]:
        if self.rid_version == RIDVersion.f3411_19:
            if not self.v19_value.has_field_with_value(
                "current_state"
            ) or not self.v19_value.current_state.has_field_with_value("speed"):
                return None
            return self.v19_value.current_state.speed
        elif self.rid_version == RIDVersion.f3411_22a:
            if not self.v22a_value.has_field_with_value(
                "current_state"
            ) or not self.v22a_value.current_state.has_field_with_value("speed"):
                return None
            return self.v22a_value.current_state.speed
        else:
            raise NotImplementedError(
                f"Cannot retrieve speed using RID version {self.rid_version}"
            )

    @property
    def timestamp(self) -> Optional[StringBasedDateTime]:
        if self.rid_version == RIDVersion.f3411_19:
            if not self.v19_value.has_field_with_value("current_state"):
                return None
            return self.v19_value.current_state.timestamp
        elif self.rid_version == RIDVersion.f3411_22a:
            if not self.v22a_value.has_field_with_value("current_state"):
                return None
            return self.v22a_value.current_state.timestamp.value
        else:
            raise NotImplementedError(
                f"Cannot retrieve speed using RID version {self.rid_version}"
            )

    def errors(self) -> List[str]:
        try:
            rid_version = self.rid_version
        except ValueError as e:
            return [str(e)]
        result = []
        if rid_version == RIDVersion.f3411_19:
            pass  # TODO: Check F3411-19 Flight data structures for errors
        elif rid_version == RIDVersion.f3411_22a:
            if (
                "current_state" in self.v22a_value
                and self.v22a_value.current_state is not None
            ):
                if "operating_area" in self.v22a_value:
                    result.append(
                        "Only one of `current_state` or `operating_area` may be specified, but both were specified"
                    )
                else:
                    current_state = self.v22a_value.current_state
                    if (
                        "position" not in current_state
                        or current_state.position is None
                    ):
                        result.append("`current_state` does not specify `position`")
                    else:
                        position = current_state.position
                        for expected_field in (
                            "lat",
                            "lng",
                            "alt",
                            "accuracy_h",
                            "accuracy_v",
                        ):
                            if (
                                expected_field not in position
                                or position[expected_field] is None
                            ):
                                result.append(
                                    f"`current_state.position.{expected_field}` is not specified"
                                )
            elif (
                "operating_area" in self.v22a_value
                and self.v22a_value.operating_area is not None
            ):
                pass  # TODO: Check operating_area data for errors
            else:
                result.append(
                    "One of `current_state` or `operating_area` must be specified, but both were unspecified"
                )
        else:
            raise NotImplementedError(
                f"Cannot check for errors in Flight object using RID version {rid_version}"
            )
        return result


class FlightDetails(ImplicitDict):
    """Version-independent representation of details for a F3411 flight."""

    v19_value: Optional[v19.api.RIDFlightDetails] = None
    v22a_value: Optional[v22a.api.RIDFlightDetails] = None

    @property
    def rid_version(self) -> RIDVersion:
        if self.v19_value is not None:
            return RIDVersion.f3411_19
        elif self.v22a_value is not None:
            return RIDVersion.f3411_22a
        else:
            raise ValueError("No valid representation was specified for flight details")

    @property
    def raw(
        self,
    ) -> Union[v19.api.RIDFlightDetails, v22a.api.RIDFlightDetails]:
        if self.rid_version == RIDVersion.f3411_19:
            return self.v19_value
        elif self.rid_version == RIDVersion.f3411_22a:
            return self.v22a_value
        else:
            raise NotImplementedError(
                f"Cannot retrieve raw flight details using RID version {self.rid_version}"
            )

    @property
    def id(self) -> str:
        return self.raw.id

    @property
    def operator_id(self) -> str:
        if self.rid_version == RIDVersion.f3411_19:
            return self.v19_value.operator_id
        elif self.rid_version == RIDVersion.f3411_22a:
            return self.v22a_value.operator_id
        else:
            raise NotImplementedError(
                f"Cannot retrieve operator_id using RID version {self.rid_version}"
            )

    @property
    def arbitrary_uas_id(self) -> Optional[str]:
        """Returns a UAS id as a plain string without type hint.
        If multiple are provided:
        For v19, registration_number is returned if set, else it falls back to the serial_number.
        For v22a, the order of ASTM F3411-v22a Table 1 is used.
        If no match, it returns None.
        """
        if self.rid_version == RIDVersion.f3411_19:
            registration_number = self.v19_value.registration_number
            if registration_number:
                return registration_number
            else:
                return self.v19_value.serial_number
        elif self.rid_version == RIDVersion.f3411_22a:
            uas_id = self.v22a_value.uas_id
            if uas_id.serial_number:
                return uas_id.serial_number
            elif uas_id.registration_id:
                return uas_id.registration_id
            elif uas_id.utm_id:
                return uas_id.utm_id
            elif uas_id.specific_session_id:
                return uas_id.specific_session_id
        else:
            raise NotImplementedError(
                f"Cannot retrieve plain_uas_id using RID version {self.rid_version}"
            )

    @property
    def operator_location(
        self,
    ) -> Optional[geo.LatLngPoint]:
        if self.rid_version == RIDVersion.f3411_19:
            if not self.v19_value.has_field_with_value("operator_location"):
                return None
            return geo.LatLngPoint(
                lat=self.v19_value.operator_location.lat,
                lng=self.v19_value.operator_location.lng,
            )
        elif self.rid_version == RIDVersion.f3411_22a:
            if not self.v22a_value.has_field_with_value("operator_location"):
                return None
            pos = self.v22a_value.operator_location.position
            return geo.LatLngPoint(lat=pos.lat, lng=pos.lng)
        else:
            raise NotImplementedError(
                f"Cannot retrieve operator_position using RID version {self.rid_version}"
            )

    @property
    def operator_altitude(
        self,
    ) -> Optional[geo.Altitude]:
        if self.rid_version == RIDVersion.f3411_19:
            return None
        elif self.rid_version == RIDVersion.f3411_22a:
            if not self.v22a_value.has_field_with_value(
                "operator_location"
            ) or not self.v22a_value.operator_location.has_field_with_value("altitude"):
                return None
            alt = self.v22a_value.operator_location.altitude
            return geo.Altitude(
                value=alt.value, reference=alt.reference, units=alt.units
            )
        else:
            raise NotImplementedError(
                f"Cannot retrieve operator_altitude using RID version {self.rid_version}"
            )

    @property
    def operator_altitude_type(
        self,
    ) -> Optional[str]:
        if self.rid_version == RIDVersion.f3411_19:
            return None
        elif self.rid_version == RIDVersion.f3411_22a:
            if not self.v22a_value.has_field_with_value(
                "operator_location"
            ) or not self.v22a_value.operator_location.has_field_with_value(
                "altitude_type"
            ):
                return None
            return self.v22a_value.operator_location.altitude_type
        else:
            raise NotImplementedError(
                f"Cannot retrieve operator_altitude_type using RID version {self.rid_version}"
            )


class Subscription(ImplicitDict):
    """Version-independent representation of a F3411 subscription."""

    v19_value: Optional[v19.api.Subscription] = None
    v22a_value: Optional[v22a.api.Subscription] = None

    @property
    def duration(self) -> Optional[datetime.timedelta]:
        if self.v19_value is not None:
            if (
                self.v19_value.time_end is not None
                and self.v19_value.time_start is not None
            ):
                return (
                    self.v19_value.time_end.datetime
                    - self.v19_value.time_start.datetime
                )
            else:
                return None
        elif self.v22a_value is not None:
            if (
                self.v22a_value.time_end is not None
                and self.v22a_value.time_start is not None
            ):
                return (
                    self.v22a_value.time_end.value.datetime
                    - self.v22a_value.time_start.value.datetime
                )
            else:
                return None
        else:
            raise ValueError("No valid representation was specified for subscription")

    @property
    def rid_version(self) -> RIDVersion:
        if self.v19_value is not None:
            return RIDVersion.f3411_19
        elif self.v22a_value is not None:
            return RIDVersion.f3411_22a
        else:
            raise ValueError("No valid representation was specified for subscription")

    @property
    def raw(
        self,
    ) -> Union[v19.api.Subscription, v22a.api.Subscription]:
        if self.rid_version == RIDVersion.f3411_19:
            return self.v19_value
        elif self.rid_version == RIDVersion.f3411_22a:
            return self.v22a_value
        else:
            raise NotImplementedError(
                f"Cannot retrieve raw subscription using RID version {self.rid_version}"
            )

    @property
    def id(self) -> str:
        return self.raw.id

    @property
    def version(self) -> str:
        return self.raw.version

    @property
    def time_start(self) -> datetime:
        if self.rid_version == RIDVersion.f3411_19:
            return self.v19_value.time_start.datetime
        elif self.rid_version == RIDVersion.f3411_22a:
            return self.v22a_value.time_start.value.datetime
        else:
            raise NotImplementedError(
                f"Cannot retrieve time_start using RID version {self.rid_version}"
            )

    @property
    def time_end(self) -> datetime:
        if self.rid_version == RIDVersion.f3411_19:
            return self.v19_value.time_end.datetime
        elif self.rid_version == RIDVersion.f3411_22a:
            return self.v22a_value.time_end.value.datetime
        else:
            raise NotImplementedError(
                f"Cannot retrieve time_end using RID version {self.rid_version}"
            )

    @property
    def isa_url(self) -> str:
        if self.rid_version == RIDVersion.f3411_19:
            return self.v19_value.callbacks.identification_service_area_url
        elif self.rid_version == RIDVersion.f3411_22a:
            isa_path = v22a.api.OPERATIONS[
                v22a.api.OperationID.PostIdentificationServiceArea
            ].path.replace("{id}", self.id)
            return self.v22a_value.uss_base_url + isa_path
        else:
            raise NotImplementedError(
                f"Cannot retrieve isa_url using RID version {self.rid_version}"
            )

    @property
    def notification_index(self) -> int:
        if self.rid_version == RIDVersion.f3411_19:
            return self.v19_value.notification_index
        elif self.rid_version == RIDVersion.f3411_22a:
            return self.v22a_value.notification_index
        else:
            raise NotImplementedError(
                f"Cannot retrieve notification_index using RID version {self.rid_version}"
            )

    @property
    def owner(self) -> str:
        if self.rid_version == RIDVersion.f3411_19:
            return self.v19_value.owner
        elif self.rid_version == RIDVersion.f3411_22a:
            return self.v22a_value.owner
        else:
            raise NotImplementedError(
                f"Cannot retrieve owner using RID version {self.rid_version}"
            )


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

    @property
    def success(self) -> bool:
        return not self.errors

    @property
    def errors(self) -> List[str]:
        raise NotImplementedError("RIDQuery.errors must be overriden")

    @property
    def participant_id(self) -> Optional[str]:
        if self.rid_version == RIDVersion.f3411_19:
            if "participant_id" in self.v19_query:
                return self.v19_query.participant_id
            else:
                return None
        elif self.rid_version == RIDVersion.f3411_22a:
            if "participant_id" in self.v22a_query:
                return self.v22a_query.participant_id
            else:
                return None
        else:
            raise NotImplementedError(
                f"Cannot retrieve participant_id using RID version {self.rid_version}"
            )

    def set_participant_id(self, participant_id: str) -> None:
        if self.v19_query is not None:
            self.v19_query.participant_id = participant_id
        elif self.v22a_query is not None:
            self.v22a_query.participant_id = participant_id
        else:
            raise NotImplementedError(f"Cannot set participant_id")


class FetchedISA(RIDQuery):
    """Version-independent representation of an ISA read from the DSS."""

    @property
    def _v19_response(
        self,
    ) -> v19.api.GetIdentificationServiceAreaResponse:
        return ImplicitDict.parse(
            self.v19_query.response.json,
            v19.api.GetIdentificationServiceAreaResponse,
        )

    @property
    def _v22a_response(
        self,
    ) -> v22a.api.GetIdentificationServiceAreaResponse:
        return ImplicitDict.parse(
            self.v22a_query.response.json,
            v22a.api.GetIdentificationServiceAreaResponse,
        )

    @property
    def errors(self) -> List[str]:
        if self.status_code == 404:
            return ["ISA not present in DSS"]
        if self.status_code != 200:
            return [f"Failed to get ISA ({self.status_code})"]
        if self.query.response.json is None:
            return ["ISA response did not include valid JSON"]

        if self.rid_version == RIDVersion.f3411_19:
            try:
                if not self._v19_response:
                    return [
                        "Unknown error with F3411-19 GetIdentificationServiceAreaResponse"
                    ]
            except ValueError as e:
                return [
                    f"Error parsing F3411-19 USS GetIdentificationServiceAreaResponse: {str(e)}"
                ]

        if self.rid_version == RIDVersion.f3411_22a:
            try:
                if not self._v22a_response:
                    return [
                        "Unknown error with F3411-22a GetIdentificationServiceAreaResponse"
                    ]
            except ValueError as e:
                return [
                    f"Error parsing F3411-22a USS GetIdentificationServiceAreaResponse: {str(e)}"
                ]

        return []

    @property
    def isa(self) -> Optional[ISA]:
        if not self.success:
            return None
        if self.rid_version == RIDVersion.f3411_19:
            return ISA(v19_value=self._v19_response.service_area)
        elif self.rid_version == RIDVersion.f3411_22a:
            return ISA(v22a_value=self._v22a_response.service_area)
        else:
            raise NotImplementedError(
                f"Cannot retrieve ISA using RID version {self.rid_version}"
            )


def isa(
    isa_id: str,
    rid_version: RIDVersion,
    session: UTMClientSession,
    dss_base_url: str = "",
    participant_id: Optional[str] = None,
) -> FetchedISA:
    if rid_version == RIDVersion.f3411_19:
        op = v19.api.OPERATIONS[v19.api.OperationID.GetIdentificationServiceArea]
        url = f"{dss_base_url}{op.path}".replace("{id}", isa_id)
        return FetchedISA(
            v19_query=fetch.query_and_describe(
                session,
                op.verb,
                url,
                scope=v19.constants.Scope.Read,
                participant_id=participant_id,
            )
        )
    elif rid_version == RIDVersion.f3411_22a:
        op = v22a.api.OPERATIONS[v22a.api.OperationID.GetIdentificationServiceArea]
        url = f"{dss_base_url}{op.path}".replace("{id}", isa_id)
        return FetchedISA(
            v22a_query=fetch.query_and_describe(
                session,
                op.verb,
                url,
                scope=v22a.constants.Scope.DisplayProvider,
                participant_id=participant_id,
            )
        )
    else:
        raise NotImplementedError(
            f"Cannot query DSS for ISA using RID version {rid_version}"
        )


class FetchedISAs(RIDQuery):
    """Version-independent representation of a list of F3411 identification service areas."""

    @property
    def _v19_response(
        self,
    ) -> v19.api.SearchIdentificationServiceAreasResponse:
        return ImplicitDict.parse(
            self.v19_query.response.json,
            v19.api.SearchIdentificationServiceAreasResponse,
        )

    @property
    def _v22a_response(
        self,
    ) -> v22a.api.SearchIdentificationServiceAreasResponse:
        return ImplicitDict.parse(
            self.v22a_query.response.json,
            v22a.api.SearchIdentificationServiceAreasResponse,
        )

    @property
    def errors(self) -> List[str]:
        # Overall errors
        if self.status_code != 200:
            return [f"Failed to search ISAs in DSS ({self.status_code})"]

        if self.query.response.json is None:
            return ["DSS response to search ISAs did not contain valid JSON"]

        if self.rid_version == RIDVersion.f3411_19:
            try:
                if not self._v19_response:
                    return [
                        "Unknown error with F3411-19 SearchIdentificationServiceAreasResponse"
                    ]
            except ValueError as e:
                return [
                    f"Error parsing F3411-19 DSS SearchIdentificationServiceAreasResponse: {str(e)}"
                ]

        if self.rid_version == RIDVersion.f3411_22a:
            try:
                if not self._v22a_response:
                    return [
                        "Unknown error with F3411-22a SearchIdentificationServiceAreasResponse"
                    ]
            except ValueError as e:
                return [
                    f"Error parsing F3411-22a DSS SearchIdentificationServiceAreasResponse: {str(e)}"
                ]

        return []

    @property
    def isas(self) -> Dict[str, ISA]:
        if not self.success:
            return {}
        if self.rid_version == RIDVersion.f3411_19:
            return {
                isa.id: ISA(v19_value=isa) for isa in self._v19_response.service_areas
            }
        elif self.rid_version == RIDVersion.f3411_22a:
            return {
                isa.id: ISA(v22a_value=isa) for isa in self._v22a_response.service_areas
            }
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
        if self.errors != other.errors:
            return True
        if self.rid_version != other.rid_version:
            return True

        if self.rid_version == RIDVersion.f3411_19:
            return self._v19_response != other._v19_response
        elif self.rid_version == RIDVersion.f3411_22a:
            return self._v22a_response != other._v22a_response
        else:
            raise NotImplementedError(
                f"Cannot compare ISAs using RID version {self.rid_version}"
            )


def isas(
    area: List[s2sphere.LatLng],
    start_time: Optional[datetime.datetime],
    end_time: Optional[datetime.datetime],
    rid_version: RIDVersion,
    session: UTMClientSession,
    dss_base_url: str = "",
    participant_id: Optional[str] = None,
) -> FetchedISAs:
    url_time_params = ""
    if start_time is not None:
        url_time_params += f"&earliest_time={rid_version.format_time(start_time)}"
    if end_time is not None:
        url_time_params += f"&latest_time={rid_version.format_time(end_time)}"

    if rid_version == RIDVersion.f3411_19:
        op = v19.api.OPERATIONS[v19.api.OperationID.SearchIdentificationServiceAreas]
        area = rid_v1.geo_polygon_string_from_s2(area)
        url = f"{dss_base_url}{op.path}?area={area}{url_time_params}"
        return FetchedISAs(
            v19_query=fetch.query_and_describe(
                session,
                op.verb,
                url,
                scope=v19.constants.Scope.Read,
                participant_id=participant_id,
            )
        )
    elif rid_version == RIDVersion.f3411_22a:
        op = v22a.api.OPERATIONS[v22a.api.OperationID.SearchIdentificationServiceAreas]
        area = rid_v2.geo_polygon_string_from_s2(area)
        url = f"{dss_base_url}{op.path}?area={area}{url_time_params}"
        return FetchedISAs(
            v22a_query=fetch.query_and_describe(
                session,
                op.verb,
                url,
                scope=v22a.constants.Scope.DisplayProvider,
                participant_id=participant_id,
            )
        )
    else:
        raise NotImplementedError(
            f"Cannot query DSS for ISA list using RID version {rid_version}"
        )


class FetchedUSSFlights(RIDQuery):
    """Version-independent representation of a list of flights reported by a USS."""

    @property
    def _v19_response(
        self,
    ) -> v19.api.GetFlightsResponse:
        return ImplicitDict.parse(
            self.v19_query.response.json,
            v19.api.GetFlightsResponse,
        )

    @property
    def _v22a_response(
        self,
    ) -> v22a.api.GetFlightsResponse:
        return ImplicitDict.parse(
            self.v22a_query.response.json,
            v22a.api.GetFlightsResponse,
        )

    @property
    def errors(self) -> List[str]:
        if self.status_code != 200:
            return ["Failed to get flights ({})".format(self.status_code)]
        if self.query.response.json is None:
            return ["Flights response did not include valid JSON"]

        if self.rid_version == RIDVersion.f3411_19:
            try:
                if not self._v19_response:
                    return ["Unknown error with F3411-19 GetFlightsResponse"]
            except ValueError as e:
                return [f"Error parsing F3411-19 USS GetFlightsResponse: {str(e)}"]

        if self.rid_version == RIDVersion.f3411_22a:
            try:
                if not self._v22a_response:
                    return ["Unknown error with F3411-22a GetFlightsResponse"]
            except ValueError as e:
                return [f"Error parsing F3411-22a USS GetFlightsResponse: {str(e)}"]

        return []

    @property
    def flights_url(self) -> str:
        return self.query.request.url.split("?")[0]

    @property
    def flights(self) -> List[Flight]:
        if not self.success:
            return []
        if self.rid_version == RIDVersion.f3411_19:
            return [Flight(v19_value=f) for f in self._v19_response.flights]
        elif self.rid_version == RIDVersion.f3411_22a:
            return [Flight(v22a_value=f) for f in self._v22a_response.flights]
        else:
            raise NotImplementedError(
                f"Cannot retrieve flights using RID version {self.rid_version}"
            )


def uss_flights(
    flights_url: str,
    area: s2sphere.LatLngRect,
    include_recent_positions: bool,
    rid_version: RIDVersion,
    session: UTMClientSession,
    participant_id: Optional[str] = None,
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
            query_type=QueryType.F3411v19Flights,
            participant_id=participant_id,
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
            query_type=QueryType.F3411v22aFlights,
            participant_id=participant_id,
        )
        return FetchedUSSFlights(v22a_query=query)
    else:
        raise NotImplementedError(
            f"Cannot query USS for flights using RID version {rid_version}"
        )


class FetchedUSSFlightDetails(RIDQuery):
    """Version-independent representation of the details of a flight reported by a USS."""

    @property
    def _v19_response(
        self,
    ) -> v19.api.GetFlightDetailsResponse:
        return ImplicitDict.parse(
            self.v19_query.response.json,
            v19.api.GetFlightDetailsResponse,
        )

    @property
    def _v22a_response(
        self,
    ) -> v22a.api.GetFlightDetailsResponse:
        return ImplicitDict.parse(
            self.v22a_query.response.json,
            v22a.api.GetFlightDetailsResponse,
        )

    @property
    def errors(self) -> List[str]:
        if self.status_code != 200:
            return ["Failed to get flight details ({})".format(self.status_code)]
        if self.query.response.json is None:
            return ["Flight details response did not include valid JSON"]

        if self.rid_version == RIDVersion.f3411_19:
            try:
                if not self._v19_response:
                    return ["Unknown error with F3411-19 GetFlightDetailsResponse"]
            except ValueError as e:
                return [
                    f"Error parsing F3411-19 USS GetFlightDetailsResponse: {str(e)}"
                ]

        if self.rid_version == RIDVersion.f3411_22a:
            try:
                if not self._v22a_response:
                    return ["Unknown error with F3411-22a GetFlightDetailsResponse"]
            except ValueError as e:
                return [
                    f"Error parsing F3411-22a USS GetFlightDetailsResponse: {str(e)}"
                ]

        return []

    @property
    def requested_id(self) -> str:
        result = self.query.request.url.split("/")[-1]
        return result.split("?")[0]

    @property
    def flights_url(self) -> str:
        return "/".join(self.query.request.url.split("/")[0:-2])

    @property
    def details(self) -> Optional[FlightDetails]:
        if not self.success:
            return None
        if self.rid_version == RIDVersion.f3411_19:
            return FlightDetails(v19_value=self._v19_response.details)
        elif self.rid_version == RIDVersion.f3411_22a:
            return FlightDetails(v22a_value=self._v22a_response.details)
        else:
            raise NotImplementedError(
                f"Cannot retrieve flight details using RID version {self.rid_version}"
            )


def flight_details(
    flights_url: str,
    flight_id: str,
    enhanced_details: bool,
    rid_version: RIDVersion,
    session: UTMClientSession,
    participant_id: Optional[str] = None,
) -> FetchedUSSFlightDetails:
    url = f"{flights_url}/{flight_id}/details"
    if rid_version == RIDVersion.f3411_19:
        kwargs = {"participant_id": participant_id}
        if enhanced_details:
            kwargs["params"] = {"enhanced": "true"}
            kwargs["scope"] = (
                v19.constants.Scope.Read + " " + rid_v1.UPP2_SCOPE_ENHANCED_DETAILS
            )
        else:
            kwargs["scope"] = v19.constants.Scope.Read
        query = fetch.query_and_describe(session, "GET", url, **kwargs)
        return FetchedUSSFlightDetails(v19_query=query)
    elif rid_version == RIDVersion.f3411_22a:
        query = fetch.query_and_describe(
            session,
            "GET",
            url,
            scope=v22a.constants.Scope.DisplayProvider,
            participant_id=participant_id,
        )
        return FetchedUSSFlightDetails(v22a_query=query)
    else:
        raise NotImplementedError(
            f"Cannot query USS for flight details using RID version {rid_version}"
        )


class FetchedFlights(ImplicitDict):
    dss_isa_query: FetchedISAs
    uss_flight_queries: Dict[str, FetchedUSSFlights]
    uss_flight_details_queries: Dict[str, FetchedUSSFlightDetails]

    @property
    def errors(self) -> List[str]:
        if not self.dss_isa_query.success:
            return self.dss_isa_query.errors
        result = []
        for flights in self.uss_flight_queries.values():
            result.extend(flights.errors)
        for uss_details in self.uss_flight_details_queries.values():
            result.extend(uss_details.errors)
        return result

    @property
    def queries(self) -> List[Query]:
        result = [self.dss_isa_query.query]
        result.extend(q.query for q in self.uss_flight_queries.values())
        result.extend(q.query for q in self.uss_flight_details_queries.values())
        return result

    @property
    def flights(self) -> List[Flight]:
        all_flights = []
        for q in self.uss_flight_queries.values():
            all_flights.extend(q.flights)
        return all_flights

    @property
    def success(self) -> bool:
        return not self.errors


def all_flights(
    area: s2sphere.LatLngRect,
    include_recent_positions: bool,
    get_details: bool,
    rid_version: RIDVersion,
    session: UTMClientSession,
    dss_base_url: str = "",
    enhanced_details: bool = False,
    dss_participant_id: Optional[str] = None,
) -> FetchedFlights:
    t = datetime.datetime.utcnow()
    isa_list = isas(
        geo.get_latlngrect_vertices(area),
        t,
        t,
        rid_version,
        session,
        dss_base_url,
        participant_id=dss_participant_id,
    )

    uss_flight_queries: Dict[str, FetchedUSSFlights] = {}
    uss_flight_details_queries: Dict[str, FetchedUSSFlightDetails] = {}
    for flights_url in isa_list.flights_urls:
        flights_for_url = uss_flights(
            flights_url,
            area,
            include_recent_positions,
            rid_version,
            session,
            # Note that we have no clue at this point which participant the flights_url is for,
            # this can only be determined later by comparing injected and observed flights.
            participant_id=None,
        )
        uss_flight_queries[flights_url] = flights_for_url

        if get_details and flights_for_url.success:
            for flight in flights_for_url.flights:
                details = flight_details(
                    flights_url,
                    flight.id,
                    enhanced_details,
                    rid_version,
                    session,
                    participant_id=None,
                )
                uss_flight_details_queries[flight.id] = details

    return FetchedFlights(
        dss_isa_query=isa_list,
        uss_flight_queries=uss_flight_queries,
        uss_flight_details_queries=uss_flight_details_queries,
    )


class FetchedSubscription(RIDQuery):
    """Version-independent representation of a Subscription read from the DSS."""

    @property
    def _v19_response(
        self,
    ) -> v19.api.GetSubscriptionResponse:
        return ImplicitDict.parse(
            self.v19_query.response.json,
            v19.api.GetSubscriptionResponse,
        )

    @property
    def _v22a_response(
        self,
    ) -> v22a.api.GetSubscriptionResponse:
        return ImplicitDict.parse(
            self.v22a_query.response.json,
            v22a.api.GetSubscriptionResponse,
        )

    @property
    def errors(self) -> List[str]:
        if self.status_code == 404:
            return ["Subscription not present in DSS"]
        if self.status_code != 200:
            return ["Failed to get Subscription ({})".format(self.status_code)]
        if self.query.response.json is None:
            return ["Subscription response did not include valid JSON"]

        if self.rid_version == RIDVersion.f3411_19:
            try:
                if not self._v19_response:
                    return ["Unknown error with F3411-19 GetSubscriptionResponse"]
            except ValueError as e:
                return [f"Error parsing F3411-19 USS GetSubscriptionResponse: {str(e)}"]

        if self.rid_version == RIDVersion.f3411_22a:
            try:
                if not self._v22a_response:
                    return ["Unknown error with F3411-22a GetSubscriptionResponse"]
            except ValueError as e:
                return [
                    f"Error parsing F3411-22a USS GetSubscriptionResponse: {str(e)}"
                ]

        return []

    @property
    def subscription(self) -> Optional[Subscription]:
        if not self.success:
            return None
        if self.rid_version == RIDVersion.f3411_19:
            return Subscription(v19_value=self._v19_response.subscription)
        elif self.rid_version == RIDVersion.f3411_22a:
            return Subscription(v22a_value=self._v22a_response.subscription)
        else:
            raise NotImplementedError(
                f"Cannot retrieve subscription using RID version {self.rid_version}"
            )


def subscription(
    subscription_id: str,
    rid_version: RIDVersion,
    session: UTMClientSession,
    dss_base_url: str = "",
    participant_id: Optional[str] = None,
) -> FetchedSubscription:
    if rid_version == RIDVersion.f3411_19:
        op = v19.api.OPERATIONS[v19.api.OperationID.GetSubscription]
        url = f"{dss_base_url}{op.path}".replace("{id}", subscription_id)
        return FetchedSubscription(
            v19_query=fetch.query_and_describe(
                session,
                op.verb,
                url,
                scope=v19.constants.Scope.Read,
                participant_id=participant_id,
            )
        )
    elif rid_version == RIDVersion.f3411_22a:
        op = v22a.api.OPERATIONS[v22a.api.OperationID.GetSubscription]
        url = f"{dss_base_url}{op.path}".replace("{id}", subscription_id)
        return FetchedSubscription(
            v22a_query=fetch.query_and_describe(
                session,
                op.verb,
                url,
                scope=v22a.constants.Scope.DisplayProvider,
                participant_id=participant_id,
            )
        )
    else:
        raise NotImplementedError(
            f"Cannot query DSS for subscription using RID version {rid_version}"
        )


class FetchedSubscriptions(RIDQuery):
    """Version-independent representation of a list of F3411 subscriptions searched from the DSS."""

    @property
    def _v19_response(
        self,
    ) -> v19.api.SearchSubscriptionsResponse:
        return ImplicitDict.parse(
            self.v19_query.response.json,
            v19.api.SearchSubscriptionsResponse,
        )

    @property
    def _v22a_response(
        self,
    ) -> v22a.api.SearchSubscriptionsResponse:
        return ImplicitDict.parse(
            self.v22a_query.response.json,
            v22a.api.SearchSubscriptionsResponse,
        )

    @property
    def errors(self) -> List[str]:
        # Overall errors
        if self.status_code != 200:
            return [f"Failed to search subscriptions in DSS ({self.status_code})"]

        if self.query.response.json is None:
            return ["DSS response to search subscriptions did not contain valid JSON"]

        if self.rid_version == RIDVersion.f3411_19:
            try:
                if not self._v19_response:
                    return ["Unknown error with F3411-19 SearchSubscriptionsResponse"]
            except ValueError as e:
                return [
                    f"Error parsing F3411-19 DSS SearchSubscriptionsResponse: {str(e)}"
                ]

        if self.rid_version == RIDVersion.f3411_22a:
            try:
                if not self._v22a_response:
                    return ["Unknown error with F3411-22a SearchSubscriptionsResponse"]
            except ValueError as e:
                return [
                    f"Error parsing F3411-22a DSS SearchSubscriptionsResponse: {str(e)}"
                ]

        return []

    @property
    def subscriptions(self) -> Dict[str, Subscription]:
        if not self.success:
            return {}
        if self.rid_version == RIDVersion.f3411_19:
            return {
                sub.id: Subscription(v19_value=sub)
                for sub in self._v19_response.subscriptions
            }
        elif self.rid_version == RIDVersion.f3411_22a:
            return {
                sub.id: Subscription(v22a_value=sub)
                for sub in self._v22a_response.subscriptions
            }
        else:
            raise NotImplementedError(
                f"Cannot search subscriptions using RID version {self.rid_version}"
            )


def subscriptions(
    area: List[s2sphere.LatLng],
    rid_version: RIDVersion,
    session: UTMClientSession,
    dss_base_url: str = "",
    participant_id: Optional[str] = None,
) -> FetchedSubscriptions:
    if rid_version == RIDVersion.f3411_19:
        op = v19.api.OPERATIONS[v19.api.OperationID.SearchSubscriptions]
        url = f"{dss_base_url}{op.path}?area={rid_v1.geo_polygon_string_from_s2(area)}"
        return FetchedSubscriptions(
            v19_query=fetch.query_and_describe(
                session,
                op.verb,
                url,
                scope=v19.constants.Scope.Read,
                participant_id=participant_id,
            )
        )
    elif rid_version == RIDVersion.f3411_22a:
        op = v22a.api.OPERATIONS[v22a.api.OperationID.SearchSubscriptions]
        url = f"{dss_base_url}{op.path}?area={rid_v2.geo_polygon_string_from_s2(area)}"
        return FetchedSubscriptions(
            v22a_query=fetch.query_and_describe(
                session,
                op.verb,
                url,
                scope=v22a.constants.Scope.DisplayProvider,
                participant_id=participant_id,
            )
        )
    else:
        raise NotImplementedError(
            f"Cannot query DSS for subscriptions using RID version {rid_version}"
        )


yaml.add_representer(FetchedISA, Representer.represent_dict)
yaml.add_representer(FetchedISAs, Representer.represent_dict)
yaml.add_representer(FetchedUSSFlights, Representer.represent_dict)
yaml.add_representer(FetchedUSSFlightDetails, Representer.represent_dict)
yaml.add_representer(FetchedFlights, Representer.represent_dict)
yaml.add_representer(FetchedSubscription, Representer.represent_dict)
yaml.add_representer(FetchedSubscriptions, Representer.represent_dict)
