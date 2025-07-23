import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

import s2sphere

from monitoring.uss_qualifier.action_generators.interuss.geospatial_map.dynamic_validator import (
    DynamicGeospatialMapValidatorConfig,
    DynamicGeospatialMapValidationAction,
    DynamicGeospatialMapValidator, # For completeness, though action is main focus
)
from monitoring.uss_qualifier.resources.geospatial_info.geospatial_info_providers import (
    GeospatialInfoProviderResource,
    GeospatialInfoProviderConfiguration, # For constructing the resource
    GeospatialInfoProviderSpecification,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_planner import (
    FlightPlannerResource,
    FlightPlannerConfiguration, # For constructing the resource
)
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import FlightIntent # For type hints
from monitoring.monitorlib.clients.flight_planning.flight_planner import PlanningActivityResult
from monitoring.monitorlib.clients.geospatial_info.client import GeospatialInfoError
from monitoring.uss_qualifier.configurations.configuration import InjectionTargetConfiguration
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.monitorlib.infrastructure import AuthAdapter


class TestDynamicGeospatialMapValidationAction(unittest.TestCase):
    def setUp(self):
        # Mock GeospatialInfoProviderResource
        self.mock_geo_provider_config = MagicMock(spec=GeospatialInfoProviderConfiguration)
        self.mock_geo_provider_config.dynamic_source_url = "http://example.com/dynamic.geojson"
        
        self.mock_geo_client = MagicMock()
        self.mock_geo_provider_resource = MagicMock(spec=GeospatialInfoProviderResource)
        self.mock_geo_provider_resource.configuration = self.mock_geo_provider_config
        self.mock_geo_provider_resource.client = self.mock_geo_client

        # Mock FlightPlannerResource
        self.mock_flight_planner_config = MagicMock(spec=FlightPlannerConfiguration)
        self.mock_flight_planner_resource = MagicMock(spec=FlightPlannerResource)
        self.mock_flight_planner_resource.configuration = self.mock_flight_planner_config
        self.mock_flight_planner_resource.auth_adapter = MagicMock(spec=AuthAdapter) # Needed by UTMClientSession
        
        # Mock FlightPlanner (the client used by the action)
        self.mock_flight_planner_client = MagicMock()
        # Patch the FlightPlanner instantiation within the action's scope
        self.flight_planner_patch = patch(
            "monitoring.uss_qualifier.action_generators.interuss.geospatial_map.dynamic_validator.FlightPlanner",
            return_value=self.mock_flight_planner_client,
        )
        self.flight_planner_patch.start()


        # Mock InjectionTargetConfiguration
        self.mock_injection_target_config = MagicMock(spec=InjectionTargetConfiguration)
        self.mock_injection_target_config.participant_id = "test-uss"
        self.mock_injection_target_config.injection_base_url = "http://test-uss.com"


        # Action Configuration
        self.action_config = DynamicGeospatialMapValidatorConfig(
            geospatial_provider=self.mock_geo_provider_resource, # Not used directly by action, but by generator
            flight_planner=self.mock_flight_planner_resource, # Not used directly by action
            injection_target=self.mock_injection_target_config,
            flight_altitude_m=100,
            flight_duration_s=60,
            flight_extent_buffer_m=10,
        )

        self.action = DynamicGeospatialMapValidationAction(
            config=self.action_config,
            geospatial_provider=self.mock_geo_provider_resource,
            flight_planner_resource=self.mock_flight_planner_resource,
        )

        self.scenario = MagicMock(spec=TestScenario)
        # Mock the check context manager
        self.mock_check_context = MagicMock()
        self.mock_check_context.__enter__.return_value = self.mock_check_context
        self.mock_check_context.__exit__.return_value = None
        self.scenario.check = self.mock_check_context


    def tearDown(self):
        self.flight_planner_patch.stop()

    def test_run_success_point_rejected(self):
        # Case 1a: Points returned, flight planning rejected (expected behavior)
        test_points = [s2sphere.LatLng.from_degrees(10, 10)]
        self.mock_geo_client.get_dynamic_test_points.return_value = test_points

        self.mock_flight_planner_client.plan_flight.return_value = MagicMock(
            spec=PlanningActivityResult, activity_result=PlanningActivityResult.Rejected, operational_intent_id="oi1"
        )

        self.action._run(self.scenario)

        self.mock_geo_client.get_dynamic_test_points.assert_called_once_with(
            source_url="http://example.com/dynamic.geojson"
        )
        self.mock_flight_planner_client.plan_flight.assert_called_once()
        self.mock_check_context.record_passed.assert_called_once()
        self.scenario.record_note.assert_any_call("dynamic_source_url", "Testing against dynamic source: http://example.com/dynamic.geojson")
        self.scenario.record_note.assert_any_call("DynamicGeospatialMapValidationAction_points_count", "Retrieved 1 test points from the dynamic source.")
        self.action.report.assert_passed.assert_called_once()


    def test_run_success_point_completed_fail(self):
        # Case 1b: Points returned, flight planning completed (unexpected behavior -> test fail for point)
        test_points = [s2sphere.LatLng.from_degrees(20, 20)]
        self.mock_geo_client.get_dynamic_test_points.return_value = test_points
        
        plan_flight_result = MagicMock(spec=PlanningActivityResult)
        plan_flight_result.activity_result = PlanningActivityResult.Completed
        plan_flight_result.operational_intent_id = "oi_completed"
        self.mock_flight_planner_client.plan_flight.return_value = plan_flight_result
        
        # Mock delete_flight for cleanup
        self.mock_flight_planner_client.delete_flight.return_value = MagicMock(spec=PlanningActivityResult, activity_result=PlanningActivityResult.Closed)


        self.action._run(self.scenario)

        self.mock_flight_planner_client.plan_flight.assert_called_once()
        self.mock_check_context.record_failed.assert_called_once()
        self.mock_flight_planner_client.delete_flight.assert_called_once_with("oi_completed", execution_context=PlanningActivityResult.Closed)
        # self.action.report.assert_failure.assert_called_once() # Overall action doesn't fail, individual check fails
        # The overall action should still pass if all checks are handled, even if some checks fail.
        # The report_passed() or report_failure() on the Action itself depends on unhandled exceptions, not check outcomes.
        # Let's verify the report object status
        self.assertEqual(self.action.report.overall_outcome, "Passed") # Action ran to completion


    def test_run_no_points_returned(self):
        # Case 2: No points returned
        self.mock_geo_client.get_dynamic_test_points.return_value = []

        self.action._run(self.scenario)

        self.scenario.record_note.assert_any_call(
            "DynamicGeospatialMapValidationAction_no_points",
            "No test points were derived from the dynamic geospatial source.",
        )
        self.action.report.assert_skipped.assert_called_once()
        self.assertEqual(self.action.report.overall_outcome, "Skipped")


    def test_run_get_points_exception(self):
        # Case 3: get_dynamic_test_points raises an exception
        self.mock_geo_client.get_dynamic_test_points.side_effect = GeospatialInfoError(
            "Failed to fetch"
        )

        self.action._run(self.scenario)

        self.scenario.record_note.assert_any_call(
            "DynamicGeospatialMapValidationAction_get_points_fail",
            "Failure while retrieving dynamic test points: Failed to fetch",
        )
        self.action.report.assert_failure.assert_called_once()
        self.assertEqual(self.action.report.overall_outcome, "Failed")


    def test_run_no_dynamic_source_url(self):
        # Case 4: dynamic_source_url not configured
        self.mock_geo_provider_config.dynamic_source_url = None # Override setup

        action_no_url = DynamicGeospatialMapValidationAction(
            config=self.action_config, # config still points to the modified mock_geo_provider_config
            geospatial_provider=self.mock_geo_provider_resource,
            flight_planner_resource=self.mock_flight_planner_resource,
        )
        action_no_url._run(self.scenario)

        self.scenario.record_note.assert_any_call(
            "DynamicGeospatialMapValidationAction_skipped",
            "Skipped as no dynamic_source_url is configured for the geospatial provider.",
        )
        action_no_url.report.assert_skipped.assert_called_once()
        self.assertEqual(action_no_url.report.overall_outcome, "Skipped")

    def test_run_flight_planning_exception(self):
        test_points = [s2sphere.LatLng.from_degrees(30, 30)]
        self.mock_geo_client.get_dynamic_test_points.return_value = test_points
        self.mock_flight_planner_client.plan_flight.side_effect = RuntimeError("USS unavailable")

        self.action._run(self.scenario)

        self.mock_check_context.record_failed.assert_called_once()
        self.scenario.record_note.assert_any_call(
            "Point_1_submission_error",
            "Error during flight submission/planning for point LatLng: degrees (30,30): USS unavailable",
        )
        # self.action.report.assert_failure.assert_called_once() # Individual check fails
        self.assertEqual(self.action.report.overall_outcome, "Passed") # Action itself completes


# Minimal test for the Generator, mainly ensuring it constructs
class TestDynamicGeospatialMapValidator(unittest.TestCase):
    def test_generator_creation_and_action_generation(self):
        mock_spec = MagicMock()
        mock_spec.action_config = MagicMock(spec=DynamicGeospatialMapValidatorConfig)
        mock_spec.resources = {
            "geospatial_provider": MagicMock(spec=GeospatialInfoProviderResource),
            "flight_planner": MagicMock(spec=FlightPlannerResource),
        }
        
        generator = DynamicGeospatialMapValidator(mock_spec)
        self.assertEqual(generator.action_type, DynamicGeospatialMapValidationAction)

        # Mock context for _generate_actions
        mock_context = MagicMock() 
        generated_actions = generator._generate_actions(mock_context)

        self.assertEqual(len(generated_actions), 1)
        self.assertIsInstance(generated_actions[0].action, DynamicGeospatialMapValidationAction)
        self.assertEqual(generated_actions[0].name, "Validate Dynamic Geospatial Data")


if __name__ == "__main__":
    unittest.main()
