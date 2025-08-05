from typing import List

import s2sphere
from implicitdict import ImplicitDict
from uas_standards.interuss.automated_testing.rid.v1.observation import (
    AltitudeReference,
    GetDisplayDataResponse,
)

from monitoring.monitorlib.fetch import Query, QueryType
from monitoring.monitorlib.geo import egm96_geoid_offset
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources.netrid import NetRIDObserversResource
from monitoring.uss_qualifier.scenarios.astm.netrid.common.nominal_behavior import (
    NominalBehavior,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario

MAXIMUM_MSL_ERROR_M = 0.5  # meters maximum difference between expected MSL altitude and reported MSL altitude
ACCEPTABLE_DATUMS = {AltitudeReference.EGM96, AltitudeReference.EGM2008}


class MSLAltitude(TestScenario):
    _ussps: List[ParticipantID]

    def __init__(self, observers: NetRIDObserversResource):
        super().__init__()
        self._ussps = [obs.participant_id for obs in observers.observers]

    def run(self, context):
        self.begin_test_scenario(context)

        self.begin_test_case("UAS observations evaluation")

        self.begin_test_step("Find nominal behavior report")
        reports = context.find_test_scenario_reports(NominalBehavior)
        self.end_test_step()

        if not reports:
            self.record_note(
                "Skip reason",
                f"Nominal behavior test scenario report could not be found for any of the scenario types {', '.join(SCENARIO_TYPES)}",
            )
            self.end_test_scenario()
            return

        self.begin_test_step("Evaluate UAS observations")
        for report in reports:
            self._evaluate_msl_altitude(report.queries())
        self.end_test_step()

        self.end_test_case()

        self.end_test_scenario()

    def _evaluate_msl_altitude(self, queries: List[Query]):
        for query in queries:
            if (
                "query_type" not in query
                or query.query_type != QueryType.InterUSSRIDObservationV1GetDisplayData
            ):
                continue
            if "json" not in query.response or not query.response.json:
                # Invalid observation; this should already have been recorded as a failure
                continue
            try:
                resp: GetDisplayDataResponse = ImplicitDict.parse(
                    query.response.json, GetDisplayDataResponse
                )
            except ValueError:
                # Invalid observation; this should already have been recorded as a failure
                continue
            if "flights" not in resp or not resp.flights:
                continue

            self.record_query(query)
            participant_id = query.participant_id if "participant_id" in query else None
            q = query.request.timestamp
            for flight in resp.flights:
                with self.check(
                    "Message contains MSL altitude", participant_id
                ) as check:
                    if (
                        "msl_alt" not in flight.most_recent_position
                        or flight.most_recent_position.msl_alt is None
                    ):
                        check.record_failed(
                            summary="MSL altitude missing from observation",
                            details=f"Flight {flight.id} was missing `msl_alt` field in the noted RID observation",
                            query_timestamps=[q],
                        )
                        continue

                with self.check(
                    "MSL altitude is reported using an acceptable datum", participant_id
                ) as check:
                    if (
                        "reference_datum" not in flight.most_recent_position.msl_alt
                        or flight.most_recent_position.msl_alt.reference_datum
                        not in ACCEPTABLE_DATUMS
                    ):
                        check.record_failed(
                            summary=f"MSL altitude reported relative to {flight.most_recent_position.msl_alt.reference_datum.value} rather than {' or '.join(ACCEPTABLE_DATUMS)}",
                            details=f"The only acceptable MSL altitude datums for U-space are {' or '.join(ACCEPTABLE_DATUMS)}, and {flight.most_recent_position.msl_alt.reference_datum.value} reported for flight {flight.id} is not one of them",
                            query_timestamps=[q],
                        )
                        continue

                if (
                    "alt" in flight.most_recent_position
                    and flight.most_recent_position is not None
                ):
                    with self.check("MSL altitude is correct", participant_id) as check:
                        geoid_offset = egm96_geoid_offset(
                            s2sphere.LatLng.from_degrees(
                                flight.most_recent_position.lat,
                                flight.most_recent_position.lng,
                            )
                        )
                        expected_msl_alt = (
                            flight.most_recent_position.alt - geoid_offset
                        )
                        if (
                            abs(
                                expected_msl_alt
                                - flight.most_recent_position.msl_alt.meters
                            )
                            > MAXIMUM_MSL_ERROR_M
                        ):
                            check.record_failed(
                                summary=f"Reported MSL altitude {flight.most_recent_position.msl_alt.meters:.1f}m does not match expected MSL altitude {expected_msl_alt:.1f}m",
                                details=f"Altitude for flight {flight.id} at {flight.most_recent_position.lat}, {flight.most_recent_position.lng} was reported as {flight.most_recent_position.alt} meters above the WGS84 ellipsoid, and the EGM96 geoid is {geoid_offset} meters above the WGS84 ellipsoid at this point, but the MSL altitude was reported as {flight.most_recent_position.msl_alt.meters} meters above {flight.most_recent_position.msl_alt.reference_datum} rather than the expected {expected_msl_alt} meters",
                                query_timestamps=[q],
                            )
                else:
                    pass
                    # TODO: check MSL altitude against injection if WGS84 altitude is not specified in observation
