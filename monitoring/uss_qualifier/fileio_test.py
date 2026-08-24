import json
import tempfile
from pathlib import Path

import yaml

from monitoring.uss_qualifier.fileio import load_dict_with_references


def test_allof_list_concatenation_issue_1661():
    """Verify that allOf concatenates lists when referenced blocks share identical keys,
    fixing the bug described in https://github.com/interuss/monitoring/issues/1661."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        definitions_file = tmp_path / "definitions.yaml"
        definitions_file.write_text(
            yaml.dump(
                {
                    "set_a": {
                        "requirement_collections": [
                            {"requirements": ["REQ_001", "REQ_002"]}
                        ]
                    },
                    "set_b": {
                        "requirement_collections": [
                            {"requirements": ["REQ_003", "REQ_004"]}
                        ]
                    },
                }
            )
        )

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "tested_requirements": [
                        {
                            "report_name": "my_results",
                            "requirement_collections": {
                                "CombinedRequirements": {
                                    "allOf": [
                                        {"$ref": f"{definitions_file}#/set_a"},
                                        {"$ref": f"{definitions_file}#/set_b"},
                                    ]
                                }
                            },
                        }
                    ]
                }
            )
        )

        result = load_dict_with_references(f"file://{config_file}")
        combined = result["tested_requirements"][0]["requirement_collections"][
            "CombinedRequirements"
        ]
        assert "allOf" not in combined
        assert combined == {
            "requirement_collections": [
                {"requirements": ["REQ_001", "REQ_002"]},
                {"requirements": ["REQ_003", "REQ_004"]},
            ]
        }


def test_allof_readme_example():
    """Verify that allOf reproduces the example documented in configurations/README.md."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        r_file = tmp_path / "r.json"
        r_file.write_text(json.dumps({"b": 5, "c": 6, "e": 7}))

        s_file = tmp_path / "s.json"
        s_file.write_text(json.dumps({"b": 8, "d": 9, "f": 10}))

        q_file = tmp_path / "q.json"
        q_file.write_text(
            json.dumps(
                {
                    "a": 1,
                    "b": 2,
                    "allOf": [{"$ref": str(r_file)}, {"$ref": str(s_file)}],
                    "c": 3,
                    "d": 4,
                }
            )
        )

        result = load_dict_with_references(f"file://{q_file}")
        assert result == {"a": 1, "b": 8, "c": 6, "d": 9, "e": 7, "f": 10}


def test_allof_deep_merge_nested_dicts_and_lists():
    """Verify recursive merging of nested dictionaries and concatenation of nested lists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        part_a = tmp_path / "a.yaml"
        part_a.write_text(
            yaml.dump(
                {
                    "nested": {
                        "key1": "val1",
                        "list1": [1, 2],
                        "inner_dict": {"x": 10, "y": 20},
                    }
                }
            )
        )

        part_b = tmp_path / "b.yaml"
        part_b.write_text(
            yaml.dump(
                {
                    "nested": {
                        "key2": "val2",
                        "list1": [3, 4],
                        "inner_dict": {"y": 30, "z": 40},
                    }
                }
            )
        )

        main_file = tmp_path / "main.yaml"
        main_file.write_text(
            yaml.dump(
                {
                    "container": {
                        "nested": {"list1": [0]},
                        "allOf": [
                            {"$ref": str(part_a)},
                            {"$ref": str(part_b)},
                        ],
                    }
                }
            )
        )

        result = load_dict_with_references(f"file://{main_file}")
        assert result == {
            "container": {
                "nested": {
                    "key1": "val1",
                    "key2": "val2",
                    "list1": [0, 1, 2, 3, 4],
                    "inner_dict": {"x": 10, "y": 30, "z": 40},
                }
            }
        }


def test_allof_internal_references():
    """Verify that allOf works with internal document references (#)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        doc_file = tmp_path / "doc.yaml"
        doc_file.write_text(
            yaml.dump(
                {
                    "definitions": {
                        "part_a": {"features": ["feat_1", "feat_2"], "score": 10},
                        "part_b": {"features": ["feat_3"], "score": 20, "extra": "yes"},
                    },
                    "combined": {
                        "allOf": [
                            {"$ref": "#/definitions/part_a"},
                            {"$ref": "#/definitions/part_b"},
                        ]
                    },
                }
            )
        )

        result = load_dict_with_references(f"file://{doc_file}")
        assert result["combined"] == {
            "features": ["feat_1", "feat_2", "feat_3"],
            "score": 20,
            "extra": "yes",
        }
