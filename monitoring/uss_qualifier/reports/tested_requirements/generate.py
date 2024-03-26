import json
import os
from typing import Dict, Set

from monitoring.monitorlib.inspection import import_submodules
from monitoring.monitorlib.versioning import get_code_version
from monitoring.uss_qualifier import scenarios, suites, action_generators
from monitoring.uss_qualifier.configurations.configuration import (
    ParticipantID,
    TestedRequirementsConfiguration,
    TestedRequirementsCollectionIdentifier,
)
from monitoring.uss_qualifier.reports import jinja_env
from monitoring.uss_qualifier.reports.report import TestRunReport
from monitoring.uss_qualifier.reports.tested_requirements.breakdown import (
    make_breakdown,
)
from monitoring.uss_qualifier.reports.tested_requirements.data_types import (
    RequirementsVerificationReport,
    ParticipantVerificationInfo,
    ParticipantVerificationStatus,
)
from monitoring.uss_qualifier.reports.tested_requirements.summaries import (
    compute_test_run_information,
    compute_overall_status,
    find_participant_system_version,
)
from monitoring.uss_qualifier.requirements.definitions import RequirementID
from monitoring.uss_qualifier.requirements.documentation import (
    resolve_requirements_collection,
)


def generate_tested_requirements(
    report: TestRunReport, config: TestedRequirementsConfiguration, output_path: str
) -> None:
    req_collections: Dict[
        TestedRequirementsCollectionIdentifier, Set[RequirementID]
    ] = {}
    if "requirement_collections" in config and config.requirement_collections:
        req_collections = {
            k: resolve_requirements_collection(v)
            for k, v in config.requirement_collections.items()
        }

    participant_req_collections: Dict[ParticipantID, Set[RequirementID]] = {}
    if "participant_requirements" in config and config.participant_requirements:
        for k, v in config.participant_requirements.items():
            if v not in req_collections:
                raise ValueError(
                    f"Participant {k}'s requirement collection {v} is not defined in `requirement_collections` of TestedRequirementsConfiguration"
                )
            participant_req_collections[k] = req_collections[v]

    import_submodules(scenarios)
    import_submodules(suites)
    import_submodules(action_generators)

    test_run = compute_test_run_information(report)

    os.makedirs(output_path, exist_ok=True)
    index_file = os.path.join(output_path, "index.html")

    participant_ids = list(report.report.participant_ids())
    participant_ids.sort()
    template = jinja_env.get_template("tested_requirements/test_run_report.html")
    with open(index_file, "w") as f:
        f.write(template.render(participant_ids=participant_ids))

    verification_report = RequirementsVerificationReport(
        test_run_information=test_run, participant_verifications={}
    )
    template = jinja_env.get_template(
        "tested_requirements/participant_tested_requirements.html"
    )
    for participant_id in participant_ids:
        req_set = participant_req_collections.get(participant_id, None)
        participant_breakdown = make_breakdown(report, req_set, participant_id)
        overall_status = compute_overall_status(participant_breakdown)
        system_version = find_participant_system_version(report.report, participant_id)
        verification_report.participant_verifications[
            participant_id
        ] = ParticipantVerificationInfo(
            status=overall_status, system_version=system_version
        )
        participant_file = os.path.join(output_path, f"{participant_id}.html")
        other_participants = ", ".join(
            p for p in participant_ids if p != participant_id
        )
        with open(participant_file, "w") as f:
            f.write(
                template.render(
                    participant_id=participant_id,
                    other_participants=other_participants,
                    breakdown=participant_breakdown,
                    test_run=test_run,
                    overall_status=overall_status,
                    system_version=system_version,
                    ParticipantVerificationStatus=ParticipantVerificationStatus,
                    codebase_version=get_code_version(),
                )
            )

    status_file = os.path.join(output_path, "status.json")
    with open(status_file, "w") as f:
        json.dump(verification_report, f, indent=2)
