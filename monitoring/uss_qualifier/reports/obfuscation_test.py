import json
import os
import tempfile

from monitoring.uss_qualifier.reports.obfuscation import (
    ObfuscatorConfig,
    find_urls,
    obfuscate_directory,
    obfuscate_json_obj,
    obfuscate_string,
    scan_text,
)


def test_find_urls():
    text = (
        "Check http://dss1.uss1.localutm/dss/v1, or go to https://github.com/interuss. "
        + "Also see (http://localhost:8082/status). And https://UPPERCASEHOST.com/foo. "
        + "With a user, we have http://user@localhost and a password too with http://user:password@localhost. "
        + "A query parameter like http://localhost?q=a2 shouldnt' hurt."
    )
    urls = find_urls(text)
    assert "http://dss1.uss1.localutm/dss/v1" in urls
    assert "https://github.com/interuss" in urls
    assert "http://localhost:8082/status" in urls
    assert "https://UPPERCASEHOST.com/foo" in urls
    assert "http://user@localhost" in urls
    assert "http://user:password@localhost" in urls
    assert "http://localhost?q=a2" in urls


def test_scan_text():
    text = "A plain url at https://UPPERCASEHOST.com/foo"
    hostnames = set()
    scan_text(text, hostnames)
    assert "uppercasehost.com" in hostnames  # urlparse converts to lowercase


def test_obfuscate_string():
    participant_map = {"uss1": "participant1", "mock_uss": "participant2"}
    hostname_map = {
        "scdsc.uss1.localutm": "host1",
        "dss1.uss1.localutm": "host2",
        "uppercasehost.com": "host3",
    }
    config = ObfuscatorConfig()

    text = "Authorization: Bearer eyJhbGci.eyJzdWIiOiJ1c3MifQ.abc-def. Also call http://scdsc.uss1.localutm/mock/scd for mock_uss and uss1. And https://UPPERCASEHOST.com/foo"
    obf = obfuscate_string(text, participant_map, hostname_map, config)

    assert "Bearer REDACTED" in obf
    assert "http://host1/mock/scd" in obf
    assert "participant2" in obf
    assert "participant1" in obf
    assert "https://host3/foo" in obf


def test_obfuscate_json_obj():
    participant_map = {"uss1": "participant1"}
    hostname_map = {"dss1.uss1.localutm": "host1"}
    config = ObfuscatorConfig()

    obj = {
        "participant_id": "uss1",
        "nested": {
            "url": "http://dss1.uss1.localutm/dss",
            "Authorization": "Bearer token123",
        },
        "list_field": ["uss1", "other"],
    }

    obfuscated = obfuscate_json_obj(obj, participant_map, hostname_map, config)
    assert obfuscated["participant_id"] == "participant1"
    assert obfuscated["nested"]["url"] == "http://host1/dss"
    assert obfuscated["nested"]["Authorization"] == "Bearer REDACTED"
    assert obfuscated["list_field"] == ["participant1", "other"]


def test_obfuscate_directory():
    config = ObfuscatorConfig()
    with (
        tempfile.TemporaryDirectory() as in_dir,
        tempfile.TemporaryDirectory() as out_dir,
    ):
        # Create a dummy structure
        report_data = {
            "participant_id": "uss1_core",
            "participants": ["uss1_core", "uss2_core"],
            "report": {
                "queries": [
                    {
                        "request": {
                            "url": "http://dss1.uss1.localutm/dss/v1",
                            "headers": {"Authorization": "Bearer mytoken"},
                        }
                    }
                ]
            },
        }

        # Write to in_dir
        with open(os.path.join(in_dir, "report.json"), "w") as f:
            json.dump(report_data, f, indent=2)

        html_content = "<html><body>Link to http://dss1.uss1.localutm/dss and uss1_core.</body></html>"
        os.makedirs(os.path.join(in_dir, "gate3"), exist_ok=True)
        with open(os.path.join(in_dir, "gate3", "uss1_core.html"), "w") as f:
            f.write(html_content)

        obfuscate_directory(in_dir, out_dir, config)

        # Verify renaming
        assert os.path.exists(os.path.join(out_dir, "gate3", "participant1.html"))

        # Verify content
        with open(os.path.join(out_dir, "gate3", "participant1.html")) as f:
            obf_html = f.read()
        assert "participant1" in obf_html
        assert "host1" in obf_html

        with open(os.path.join(out_dir, "report.json")) as f:
            obf_json = json.load(f)
        assert obf_json["participant_id"] == "participant1"
        assert (
            obf_json["report"]["queries"][0]["request"]["url"] == "http://host1/dss/v1"
        )
        assert (
            obf_json["report"]["queries"][0]["request"]["headers"]["Authorization"]
            == "Bearer REDACTED"
        )
