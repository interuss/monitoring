import unittest
from unittest.mock import MagicMock

from monitoring.uss_qualifier.resources.geospatial_info.geospatial_info_providers import (
    GeospatialInfoProviderConfiguration,
    GeospatialInfoProviderResource, # For context, not directly tested here
    GeospatialInfoProviderSpecification,
)
from monitoring.monitorlib.clients.geospatial_info.client_geospatial_map import (
    GeospatialMapClient,
)
from monitoring.monitorlib.infrastructure import AuthAdapter


class TestGeospatialInfoProviderConfiguration(unittest.TestCase):
    def test_init_valid_dynamic_url(self):
        try:
            GeospatialInfoProviderConfiguration(
                participant_id="test_participant",
                dynamic_source_url="http://example.com/source.geojson",
            )
        except ValueError:
            self.fail("ValueError raised unexpectedly for valid dynamic_source_url")

    def test_init_invalid_dynamic_url(self):
        with self.assertRaises(ValueError) as context:
            GeospatialInfoProviderConfiguration(
                participant_id="test_participant",
                dynamic_source_url="not a valid url",
            )
        self.assertIn(
            "GeospatialInfoProviderConfiguration.dynamic_source_url must be a URL",
            str(context.exception),
        )

    def test_init_valid_static_url(self):
        try:
            GeospatialInfoProviderConfiguration(
                participant_id="test_participant",
                geospatial_map_v1_base_url="http://example.com/api/v1",
            )
        except ValueError:
            self.fail(
                "ValueError raised unexpectedly for valid geospatial_map_v1_base_url"
            )

    def test_init_invalid_static_url(self):
        with self.assertRaises(ValueError) as context:
            GeospatialInfoProviderConfiguration(
                participant_id="test_participant",
                geospatial_map_v1_base_url="not a valid url",
            )
        self.assertIn(
            "GeospatialInfoProviderConfiguration.geospatial_map_v1_base_url must be a URL",
            str(context.exception),
        )

    def test_to_client_dynamic_only(self):
        mock_auth_adapter = MagicMock(spec=AuthAdapter)
        config = GeospatialInfoProviderConfiguration(
            participant_id="test_dynamic_provider",
            dynamic_source_url="http://example.com/dynamic.geojson",
            dynamic_source_type="geojson",
            dynamic_source_interpretation_rule="treat_all_as_restrictions",
        )
        client = config.to_client(mock_auth_adapter)
        self.assertIsInstance(client, GeospatialMapClient)
        self.assertEqual(client.participant_id, "test_dynamic_provider")
        # Check if dynamic source related fields are passed to client's constructor
        # The actual GeospatialMapClient constructor stores these with leading underscores
        self.assertEqual(client._dynamic_source_url, "http://example.com/dynamic.geojson")
        self.assertEqual(client._dynamic_source_type, "geojson")
        self.assertEqual(client._dynamic_source_interpretation_rule, "treat_all_as_restrictions")
        # The session's base_url for dynamic-only config is set to the dynamic_source_url
        self.assertEqual(client._session.base_url, "http://example.com/dynamic.geojson")


    def test_to_client_static_only(self):
        mock_auth_adapter = MagicMock(spec=AuthAdapter)
        config = GeospatialInfoProviderConfiguration(
            participant_id="test_static_provider",
            geospatial_map_v1_base_url="http://static.example.com/api/v1",
        )
        client = config.to_client(mock_auth_adapter)
        self.assertIsInstance(client, GeospatialMapClient)
        self.assertEqual(client.participant_id, "test_static_provider")
        self.assertEqual(client._session.base_url, "http://static.example.com/api/v1")
        # Dynamic fields should be None
        self.assertIsNone(client._dynamic_source_url)
        self.assertIsNone(client._dynamic_source_type)
        self.assertIsNone(client._dynamic_source_interpretation_rule)

    def test_to_client_both_static_and_dynamic(self):
        mock_auth_adapter = MagicMock(spec=AuthAdapter)
        config = GeospatialInfoProviderConfiguration(
            participant_id="test_both_provider",
            geospatial_map_v1_base_url="http://static.example.com/api/v1",
            dynamic_source_url="http://dynamic.example.com/data.geojson",
            dynamic_source_type="geojson_custom",
        )
        client = config.to_client(mock_auth_adapter)
        self.assertIsInstance(client, GeospatialMapClient)
        self.assertEqual(client.participant_id, "test_both_provider")
        # Static base URL should be preferred for session if available
        self.assertEqual(client._session.base_url, "http://static.example.com/api/v1")
        # Dynamic fields should also be set
        self.assertEqual(client._dynamic_source_url, "http://dynamic.example.com/data.geojson")
        self.assertEqual(client._dynamic_source_type, "geojson_custom")
        self.assertIsNone(client._dynamic_source_interpretation_rule) # Not set in this config

    def test_to_client_neither_configured(self):
        mock_auth_adapter = MagicMock(spec=AuthAdapter)
        config = GeospatialInfoProviderConfiguration(
            participant_id="test_neither_provider"
        )
        # Manually remove any default-set optional fields if necessary for the test condition
        if hasattr(config, "geospatial_map_v1_base_url"):
            delattr(config, "geospatial_map_v1_base_url")
        if hasattr(config, "dynamic_source_url"):
            delattr(config, "dynamic_source_url")
            
        with self.assertRaises(ValueError) as context:
            config.to_client(mock_auth_adapter)
        self.assertIn(
            "Could not construct GeospatialInfoClient from provided configuration",
            str(context.exception),
        )


if __name__ == "__main__":
    unittest.main()
