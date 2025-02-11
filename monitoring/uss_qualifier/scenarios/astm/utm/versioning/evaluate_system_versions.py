from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Tuple

from implicitdict import ImplicitDict
from uas_standards.interuss.automated_testing.versioning.api import GetVersionResponse

from monitoring.monitorlib.clients.versioning.client import VersionQueryError
from monitoring.monitorlib.fetch import Query, QueryType
from monitoring.uss_qualifier.configurations.configuration import ParticipantID
from monitoring.uss_qualifier.resources.versioning import SystemIdentityResource
from monitoring.uss_qualifier.resources.versioning.client import (
    VersionProvidersResource,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


@dataclass
class _VersionInfo(object):
    participant_id: ParticipantID
    version: str
    query: Query


class EvaluateSystemVersions(TestScenario):
    def __init__(
        self,
        system_identity: SystemIdentityResource,
        test_env_version_providers: VersionProvidersResource,
        prod_env_version_providers: VersionProvidersResource,
    ):
        super(EvaluateSystemVersions, self).__init__()
        self._test_env_version_providers = test_env_version_providers.version_providers
        self._prod_env_version_providers = prod_env_version_providers.version_providers
        self._system_identity = system_identity.system_identity

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self.begin_test_case("Evaluate versions")

        test_env_versions, prod_env_versions = self._get_versions()
        self._evaluate_versions(test_env_versions, prod_env_versions)
        self._evaluate_consistency(context, test_env_versions)

        self.end_test_case()
        self.end_test_scenario()

    def _get_versions(
        self,
    ) -> Tuple[Dict[ParticipantID, _VersionInfo], Dict[ParticipantID, _VersionInfo]]:
        test_env_versions: Dict[ParticipantID, _VersionInfo] = {}
        prod_env_versions: Dict[ParticipantID, _VersionInfo] = {}

        for (test_step, version_providers, env_versions) in (
            (
                "Get test environment test versions",
                self._test_env_version_providers,
                test_env_versions,
            ),
            (
                "Get production environment versions",
                self._prod_env_version_providers,
                prod_env_versions,
            ),
        ):
            self.begin_test_step(test_step)

            for version_provider in version_providers:
                with self.check(
                    "Valid response", participants=[version_provider.participant_id]
                ) as check:
                    try:
                        resp = version_provider.get_version(self._system_identity)
                        self.record_query(resp.query)
                        env_versions[version_provider.participant_id] = _VersionInfo(
                            participant_id=version_provider.participant_id,
                            version=resp.version,
                            query=resp.query,
                        )
                    except VersionQueryError as e:
                        for q in e.queries:
                            self.record_query(q)
                        check.record_failed(
                            summary="Error querying version",
                            details=str(e),
                            query_timestamps=[q.request.timestamp for q in e.queries],
                        )

            self.end_test_step()
        return test_env_versions, prod_env_versions

    def _evaluate_versions(
        self,
        test_env_versions: Dict[ParticipantID, _VersionInfo],
        prod_env_versions: Dict[ParticipantID, _VersionInfo],
    ):
        self.begin_test_step("Evaluate current system versions")

        mismatched_participants = []
        matched_participants = []
        for participant_id in test_env_versions:
            if participant_id not in prod_env_versions:
                self.record_note(
                    f"{participant_id} prod system",
                    f"The production version of {participant_id}'s system could not be determined (perhaps because of means of determining the production version was not provided)'",
                )
                continue
            if (
                test_env_versions[participant_id].version
                == prod_env_versions[participant_id].version
            ):
                matched_participants.append(participant_id)
            else:
                mismatched_participants.append(participant_id)
        for participant_id in matched_participants:
            with self.check(
                "Test software version matches production",
                participants=participant_id,
            ) as check:
                check.record_passed()

        if len(mismatched_participants) == 1:
            self.record_note(
                "Participant testing new software", mismatched_participants[0]
            )
            # Move technically-mismatched participant over to matched participants to prepare for one-at-a-time check
            matched_participants.append(mismatched_participants[0])
            mismatched_participants.clear()

        # Record appropriate failures for participants with mismatched software versions (when there are 2 or more)
        mismatch_timestamps = []
        for participant_id in mismatched_participants:
            timestamps = [
                test_env_versions[participant_id].query.request.timestamp,
                prod_env_versions[participant_id].query.request.timestamp,
            ]
            with self.check(
                "Test software version matches production", participants=participant_id
            ) as check:
                check.record_failed(
                    summary="Test environment software version does not match production",
                    details=f"{participant_id} indicated version '{test_env_versions[participant_id].version}' in the test environment and version '{prod_env_versions[participant_id].version}' in the production environment.",
                    query_timestamps=timestamps,
                )
            mismatch_timestamps.extend(timestamps)

        # Record one-at-a-time check result
        if mismatched_participants:
            with self.check(
                "At most one participant is testing a new software version",
                participants=mismatched_participants,
            ) as check:
                check.record_failed(
                    summary="Test environment software version does not match production",
                    details=f"At most, only one participant may be testing a software version that differs from production, but {', '.join(mismatched_participants)} all had differing versions between environments.",
                    query_timestamps=mismatch_timestamps,
                )
        else:
            with self.check(
                "At most one participant is testing a new software version",
                participants=matched_participants,
            ) as check:
                check.record_passed()

        self.end_test_step()

    def _evaluate_consistency(
        self,
        context: ExecutionContext,
        test_env_versions: Dict[ParticipantID, _VersionInfo],
    ):
        self.begin_test_step("Evaluate system version consistency")
        for q in context.sibling_queries():
            if (
                "query_type" not in q
                or q.query_type != QueryType.InterUSSVersioningGetVersion
                or "participant_id" not in q
            ):
                continue
            if (
                q.participant_id in test_env_versions
                and q.request.url
                == test_env_versions[q.participant_id].query.request.url
            ):
                try:
                    resp = ImplicitDict.parse(q.response.json, GetVersionResponse)
                except (ValueError, KeyError):
                    # Something was wrong with the response payload; ignore this query
                    continue
                with self.check(
                    "Software versions are consistent throughout test run",
                    participants=q.participant_id,
                ) as check:
                    if (
                        resp.system_version
                        != test_env_versions[q.participant_id].version
                    ):
                        check.record_failed(
                            summary="Version of software under test changed during test run",
                            details=f"When queried for the version of the '{self._system_identity}' system, earlier response indicated '{resp.system_version}' but later response indicated '{test_env_versions[q.participant_id].version}'",
                            query_timestamps=[
                                q.request.timestamp,
                                test_env_versions[
                                    q.participant_id
                                ].query.request.timestamp,
                            ],
                        )

        self.end_test_step()
