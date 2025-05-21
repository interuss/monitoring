from datetime import timedelta, datetime
from typing import List, Optional

import s2sphere
from implicitdict import ImplicitDict

from uas_standards.astm.f3548.v21.api import OperationalIntentState
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.geo import Circle, Altitude, Volume3D, LatLngPoint
from monitoring.monitorlib.geotemporal import Time, Volume4D
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.monitorlib.clients.flight_planning.flight_info import FlightInfo
from monitoring.monitorlib.clients.flight_planning.flight_planner import (
    FlightPlanner,
    PlanningActivityResult,
)
from monitoring.monitorlib.clients.flight_planning.test_preparation import (
    prepare_flight_conflict_test,
)


from monitoring.uss_qualifier.action_generators.action_generator import (
    ActionGenerator,
    ActionGeneratorSpecification,
    create_tests_from_actions,
)
from monitoring.uss_qualifier.actions.action import Action, ActionReport
from monitoring.uss_qualifier.configurations.configuration import InjectionTargetConfiguration
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.flight_planner import (
    FlightPlannerResource,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntent,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_planner import (
    FlightPlannerResource as FlightPlannerResourceInterface,
)
from monitoring.uss_qualifier.resources.geospatial_info.geospatial_info_providers import (
    GeospatialInfoProviderResource,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext

# Default flight parameters for testing geospatial restrictions
DEFAULT_FLIGHT_ALTITUDE_M = 50  # Default altitude in meters AGL
DEFAULT_FLIGHT_DURATION_S = 60  # Default duration of the test flight in seconds
DEFAULT_FLIGHT_BUFFER_M = 15    # Default buffer around the point for the flight volume in meters


class DynamicGeospatialMapValidatorConfig(ImplicitDict):
    """Configuration for the DynamicGeospatialMapValidator action generator."""

    geospatial_provider: GeospatialInfoProviderResource
    """Resource providing geospatial information, configured with a dynamic source."""

    flight_planner: FlightPlannerResource
    """Resource representing the flight planner for the USS under test."""

    injection_target: InjectionTargetConfiguration
    """Configuration for the injection target (USS being tested)."""

    flight_altitude_m: Optional[float] = DEFAULT_FLIGHT_ALTITUDE_M
    """Altitude in meters AGL for the test flight intents."""

    flight_duration_s: Optional[int] = DEFAULT_FLIGHT_DURATION_S
    """Duration in seconds for the test flight intents."""

    flight_extent_buffer_m: Optional[float] = DEFAULT_FLIGHT_BUFFER_M
    """Buffer in meters around the test point to define the flight volume."""

    wait_for_operational_intent: Optional[bool] = True
    """Whether to wait for the operational intent to be created and verify its state."""


class DynamicGeospatialMapValidationAction(Action):
    """Action that validates USS behavior against a dynamic geospatial data source."""

    _config: DynamicGeospatialMapValidatorConfig
    _geospatial_provider: GeospatialInfoProviderResource
    _flight_planner_resource: FlightPlannerResource # For creating FlightIntents via FlightPlanner
    _uss_client_session: UTMClientSession # For direct interaction if needed, or via FlightPlannerResource

    def __init__(
        self,
        config: DynamicGeospatialMapValidatorConfig,
        geospatial_provider: GeospatialInfoProviderResource,
        flight_planner_resource: FlightPlannerResource,
        # TODO: May need SCDInjectionResource or similar for direct submissions if not using FlightPlannerResource for everything
    ):
        super().__init__()
        self._config = config
        self._geospatial_provider = geospatial_provider
        self._flight_planner_resource = flight_planner_resource
        
        # Initialize a UTMClientSession for the USS under test
        self._uss_client_session = UTMClientSession(
            self._config.injection_target.injection_base_url,
            self._flight_planner_resource.auth_adapter, # Assuming auth_adapter is suitable
        )


    def _run(self, scenario: TestScenario):
        self.report_new_capability(
            name="Validate against dynamic geospatial source",
            description="This test validates if the USS correctly handles restrictions from a dynamic GeoJSON source by attempting to plan flights in areas derived from this source.",
            capability_id="DYNAMIC_GEOSPATIAL_VALIDATION" # Arbitrary ID
        )

        if not self._geospatial_provider.configuration.dynamic_source_url:
            scenario.record_note(
                "DynamicGeospatialMapValidationAction_skipped",
                "Skipped as no dynamic_source_url is configured for the geospatial provider.",
            )
            self.report_skipped(
                "No dynamic_source_url configured for geospatial provider."
            )
            return

        scenario.record_note(
            "dynamic_source_url",
            f"Testing against dynamic source: {self._geospatial_provider.configuration.dynamic_source_url}",
        )

        try:
            test_points = self._geospatial_provider.client.get_dynamic_test_points(
                source_url=self._geospatial_provider.configuration.dynamic_source_url
            )
        except Exception as e:
            scenario.record_note(
                "DynamicGeospatialMapValidationAction_get_points_fail",
                f"Failure while retrieving dynamic test points: {e}",
            )
            self.report_failure(f"Failed to get dynamic test points: {e}")
            return

        if not test_points:
            scenario.record_note(
                "DynamicGeospatialMapValidationAction_no_points",
                "No test points were derived from the dynamic geospatial source.",
            )
            self.report_skipped(
                "No test points derived from the dynamic geospatial source."
            )
            return
        
        scenario.record_note(
            "DynamicGeospatialMapValidationAction_points_count",
            f"Retrieved {len(test_points)} test points from the dynamic source.",
        )

        flight_planner = FlightPlanner(
            self._flight_planner_resource.client, self._flight_planner_resource.auth_adapter
        )

        overall_success = True
        for i, point in enumerate(test_points):
            with scenario.check(f"Geospatial restriction at point {i+1}", [self._config.injection_target.participant_id]) as check:
                # Define the flight volume for the test point
                center_latlng = LatLngPoint(lat=point.lat().degrees, lng=point.lng().degrees)
                circle_radius = self._config.flight_extent_buffer_m
                altitude_lower = self._config.flight_altitude_m - 5 # e.g., 5m buffer
                altitude_upper = self._config.flight_altitude_m + 5
                
                volume3d = Volume3D(
                    outline_circle=Circle.from_meters(center_latlng, circle_radius),
                    altitude_lower=Altitude.w84m(altitude_lower), # AGL assumed, but W84 for API
                    altitude_upper=Altitude.w84m(altitude_upper),
                )
                
                # Define time window (e.g., starting now for a short duration)
                # Note: USS might require start_time to be slightly in the future.
                # For simplicity, using a small offset from now.
                time_start = Time(datetime.utcnow() + timedelta(seconds=20)) # Offset by 20s
                time_end = Time(time_start.datetime + timedelta(seconds=self._config.flight_duration_s))
                volume4d = Volume4D(volume=volume3d, time_start=time_start, time_end=time_end)

                flight_intent = FlightIntent.from_flightinfo(
                    flightinfo=FlightInfo(
                        uas_id="DynamicGeospatialTest", # Generic UAS ID
                        operator_id=self._config.injection_target.participant_id, # Or a generic operator ID
                        volumes=[volume4d],
                        priority=1, # Arbitrary priority
                        state=OperationalIntentState.Accepted, # Desired initial state for planning
                        off_nominal_volumes=[],
                        constraints=[], # No specific constraints for this test
                    ),
                    astm_f3548_v21_scopes=[Scope.StrategicConflictDetection],
                )
                
                scenario.record_note(
                    f"Point_{i+1}_details",
                    f"Testing point: ({point.lat().degrees}, {point.lng().degrees}). Flight Volume: {volume4d.to_json()}",
                )

                try:
                    # Using FlightPlanner to plan the flight.
                    # This assumes the FlightPlanner resource is for the USS under test.
                    # The expectation is that this planning should fail or result in a non-Accepted state
                    # if the area is indeed restricted according to the dynamic source.
                    planning_result = flight_planner.plan_flight(
                        flight_intent, execution_context=PlanningActivityResult.Planned # Expecting a planned state if successful
                    )
                    
                    if planning_result.activity_result == PlanningActivityResult.Completed:
                        # Flight planned successfully - this means the area was NOT seen as restricted by the USS.
                        # This is a failure for this test if the dynamic source implies a restriction.
                        scenario.record_note(
                            f"Point_{i+1}_unexpected_success",
                            f"Flight planned successfully at restricted point {point}. Operational Intent ID: {planning_result.operational_intent_id}",
                        )
                        check.record_failed(
                            summary=f"USS allowed flight creation at a dynamically restricted point {i+1}",
                            details=f"Point: ({point.lat().degrees}, {point.lng().degrees}). USS planned flight {planning_result.operational_intent_id} which should have been recognized as restricted.",
                            query_timestamps=[datetime.utcnow()] 
                        )
                        overall_success = False
                        # Cleanup: Attempt to delete the operational intent
                        try:
                            flight_planner.delete_flight(planning_result.operational_intent_id, execution_context=PlanningActivityResult.Closed)
                        except Exception as del_e:
                            scenario.record_note(f"Point_{i+1}_cleanup_failed", f"Failed to delete op intent {planning_result.operational_intent_id}: {del_e}")

                    elif planning_result.activity_result in [PlanningActivityResult.Rejected, PlanningActivityResult.Failed, PlanningActivityResult.NotSupported]:
                        # Flight planning was rejected or failed - this is the expected outcome.
                        scenario.record_note(
                            f"Point_{i+1}_expected_rejection",
                            f"Flight planning correctly rejected/failed at restricted point {point}. Reason: {planning_result.get('error_report', 'N/A')}",
                        )
                        check.record_passed(
                            summary=f"USS correctly prevented flight creation at dynamically restricted point {i+1}",
                            details=f"Point: ({point.lat().degrees}, {point.lng().degrees}). Reason: {planning_result.get('error_report', 'N/A')}"
                        )
                    else: # Other outcomes like TimedOut, etc.
                        scenario.record_note(
                            f"Point_{i+1}_unexpected_outcome",
                            f"Flight planning at restricted point {point} resulted in an unexpected state: {planning_result.activity_result}. Details: {planning_result.get('error_report', 'N/A')}",
                        )
                        check.record_failed(
                            summary=f"USS flight planning had an unexpected outcome ({planning_result.activity_result}) at dynamically restricted point {i+1}",
                            details=f"Point: ({point.lat().degrees}, {point.lng().degrees}). Details: {planning_result.get('error_report', 'N/A')}",
                            query_timestamps=[datetime.utcnow()]
                        )
                        overall_success = False

                except Exception as e:
                    scenario.record_note(
                        f"Point_{i+1}_submission_error",
                        f"Error during flight submission/planning for point {point}: {e}",
                    )
                    check.record_failed(
                        summary=f"Error submitting/planning flight for dynamically restricted point {i+1}",
                        details=str(e),
                        query_timestamps=[datetime.utcnow()]
                    )
                    overall_success = False
        
        if overall_success:
            self.report_passed()
        else:
            # Failure has already been reported by the failing check
            pass # No need to call self.report_failure() as individual checks handle it.


class DynamicGeospatialMapValidator(ActionGenerator[DynamicGeospatialMapValidatorConfig]):
    """
    Action generator that creates `DynamicGeospatialMapValidationAction` instances
    to validate a USS against a dynamic geospatial data source.
    """

    def __init__(self, specification: ActionGeneratorSpecification[DynamicGeospatialMapValidatorConfig]):
        super().__init__(specification)

    @property
    def action_type(self) -> type[DynamicGeospatialMapValidationAction]:
        return DynamicGeospatialMapValidationAction

    def _generate_actions(
        self,
        context: ExecutionContext, # Formerly TestRunPlanningOptions
    ) -> List[ActionGenerator.GeneratedAction]:
        
        action = self.action_type(
            config=self.specification.action_config,
            geospatial_provider=self.specification.resources["geospatial_provider"],
            flight_planner_resource=self.specification.resources["flight_planner"],
        )
        return [ActionGenerator.GeneratedAction(action=action, name="Validate Dynamic Geospatial Data")]


def create_test_scenario(
    scenario_name: str,
    action_generator: DynamicGeospatialMapValidator,
    geospatial_provider: GeospatialInfoProviderResource,
    flight_planner: FlightPlannerResource,
    injection_target: InjectionTargetConfiguration,
) -> TestScenario:
    """
    Helper function to create a TestScenario with the DynamicGeospatialMapValidator.
    This is more for illustrative purposes or direct script usage.
    """
    spec = ActionGeneratorSpecification(
        action_type="DynamicGeospatialMapValidator", # This would be the registered name
        action_config=DynamicGeospatialMapValidatorConfig(
            geospatial_provider=geospatial_provider, # Just for config, actual resource passed below
            flight_planner=flight_planner,           # Just for config, actual resource passed below
            injection_target=injection_target
        ),
        resources={
            "geospatial_provider": geospatial_provider,
            "flight_planner": flight_planner,
        }
    )
    # Manually creating the generator instance for this helper
    generator_instance = DynamicGeospatialMapValidator(spec)
    
    # In a real setup, actions would be generated via a TestSuite and TestRun.
    # Here, we simulate a part of that for direct scenario creation.
    # The `create_tests_from_actions` function expects a list of GeneratedAction objects.
    generated_actions = generator_instance._generate_actions(context=None) # Context might be needed for more complex scenarios
    
    return TestScenario(
        name=scenario_name,
        actions=create_tests_from_actions(generated_actions) # This helper might need adjustment based on its actual signature
    )

# Example usage (conceptual, normally configured via test suite YAML)
# if __name__ == "__main__":
#     # This section is for conceptual illustration and would not be part of the PR in this form.
#     # It shows how one might set up and "run" this scenario programmatically.
# 
#     # Mock/Dummy Resources (replace with actual resource loading in a test environment)
#     dummy_geo_provider_config = GeospatialInfoProviderConfiguration(
#         participant_id="test_geo_provider",
#         dynamic_source_url="http://example.com/dynamic_restrictions.geojson" 
#     )
#     dummy_geo_provider_resource = GeospatialInfoProviderResource(
#         specification=GeospatialInfoProviderSpecification(geospatial_info_provider=dummy_geo_provider_config),
#         # ... other required fields for resource initialization
#     )
# 
#     dummy_flight_planner_config = FlightPlannerConfiguration(
#         participant_id="test_uss",
#         injection_base_url="http://test-uss.example.com/f3548v21",
#         # ... other fields
#     )
#     dummy_flight_planner_resource = FlightPlannerResource(
#         specification=FlightPlannerSpecification(target=dummy_flight_planner_config),
#         # ... other required fields
#     )
#     
#     dummy_injection_target = InjectionTargetConfiguration(
#         name="TestUSS",
#         participant_id="test_uss",
#         injection_base_url="http://test-uss.example.com/f3548v21",
#     )
# 
#     # Create the scenario
#     # Note: The ActionGeneratorSpecification would typically be loaded from a config file.
#     # For this example, we are constructing it manually.
#     
#     scenario_spec = ActionGeneratorSpecification(
#         action_type='interuss.geospatial_map.DynamicGeospatialMapValidator', # Fictional registered name
#         action_config=DynamicGeospatialMapValidatorConfig(
#             geospatial_provider=None, # Not used directly by config, resource is looked up
#             flight_planner=None,    # Not used directly by config, resource is looked up
#             injection_target=dummy_injection_target,
#             flight_altitude_m=100,
#             flight_duration_s=30,
#             flight_extent_buffer_m=20
#         )
#     )
# 
#     dynamic_validator_generator = DynamicGeospatialMapValidator(scenario_spec)
# 
#     # Create a TestScenario instance (simplified)
#     # The actual creation involves more context and resource management from the test runner.
#     # test_scenario = TestScenario(
#     #     name="DynamicGeospatialDataCheck",
#     #     actions=dynamic_validator_generator.generate_actions(None) # Context would be TestRunPlanningOptions
#     # )
#     
#     # To "run" this, you'd typically use the test execution framework.
#     # test_scenario.execute(None) # Dummy execution context
# 
#     print("DynamicGeospatialMapValidator structure created.")
#     print("To use this, it needs to be registered and configured within the test execution framework.")
