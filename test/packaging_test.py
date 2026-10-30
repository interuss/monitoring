"""Smoke checks for an installed wheel; run with `python -I test/packaging_test.py`."""

import unittest
from importlib.metadata import distribution

from s2sphere import LatLng

from monitoring.monitorlib.fileio import load_dict_with_references
from monitoring.monitorlib.geo import Circle, Volume3D, egm96_geoid_offset
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.kml.generation import make_placemark_from_volume
from monitoring.uss_qualifier import package_root
from monitoring.uss_qualifier.reports import jinja_env
from monitoring.uss_qualifier.requirements.definitions import RequirementID
from monitoring.uss_qualifier.requirements.documentation import get_requirement
from monitoring.uss_qualifier.scenarios.dev.noop import NoOp
from monitoring.uss_qualifier.scenarios.documentation.parsing import get_documentation


class InstalledWheelTest(unittest.TestCase):
    # This test is AI-generated and has not been closely inspected by a human.
    def test_geoid_and_kml(self):
        self.assertAlmostEqual(egm96_geoid_offset(LatLng.from_degrees(0, 0)), 17.16)
        volume = Volume4D(volume=Volume3D(outline_circle=Circle.from_meters(0, 0, 100)))
        placemark = make_placemark_from_volume(volume, name="Packaged volume")
        self.assertEqual(placemark.name.text, "Packaged volume")
        self.assertTrue(len(placemark.MultiGeometry))

    # This test is AI-generated and has not been closely inspected by a human.
    def test_templates(self):
        for name in jinja_env.list_templates():
            with self.subTest(template=name):
                jinja_env.get_template(name)
        explorer = jinja_env.from_string(
            '{% from "explorer.html" import explorer_content %}'
            '{{ explorer_content("packaging-test", {"key": "Packaged value"}) }}'
        )
        self.assertIn("Packaged value", explorer.render())
        self.assertTrue(
            jinja_env.get_template("ai_helpers/AGENTS.md.template").render()
        )

    # This test is AI-generated and has not been closely inspected by a human.
    def test_qualifier_definitions(self):
        self.assertEqual(get_documentation(NoOp).name, "NoOp")
        requirement_id = RequirementID("interuss.uss_qualifier.unit_test.REQ001")
        self.assertEqual(get_requirement(requirement_id).requirement_id, requirement_id)
        suite = load_dict_with_references("suites.astm.utm.f3548_21", package_root)
        self.assertTrue(suite["actions"])

    # This test is AI-generated and has not been closely inspected by a human.
    def test_distribution_contents(self):
        paths = {str(path) for path in distribution("interuss_monitoring").files or []}
        self.assertIn("monitoring/monitorlib/assets/WW15MGH.DAC", paths)
        self.assertIn("monitoring/mock_uss/templates/ui/logged_in.html", paths)
        self.assertIn("monitoring/prober/scd/resources/op_request_1.json", paths)
        for path in paths:
            if not path.startswith("monitoring/"):
                continue
            with self.subTest(path=path):
                self.assertFalse(path.endswith((".sh", ".key", ".crt")))
                self.assertNotIn("/output/", path)
                if not path.endswith(".py"):
                    self.assertNotIn("/configurations/", path)


if __name__ == "__main__":
    unittest.main()
