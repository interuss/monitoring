from .definitions import RequirementCollection, RequirementSetID
from .documentation import get_requirement_set, resolve_requirements_collection


def test_requirements_extraction():
    collection = RequirementSetID("interuss.uss_qualifier.unit_test.set1")
    requirement_set = get_requirement_set(collection)
    assert len(requirement_set.requirement_ids) == 3

    collection = RequirementSetID("interuss.uss_qualifier.unit_test.set1#Manual Checks")
    requirement_set = get_requirement_set(collection)
    assert len(requirement_set.requirement_ids) == 1

    collection = RequirementSetID(
        "interuss.uss_qualifier.unit_test.set1#Automated Checks"
    )
    requirement_set = get_requirement_set(collection)
    assert len(requirement_set.requirement_ids) == 2
