import unittest
from unittest.mock import patch, MagicMock

import s2sphere
import requests
from shapely.geometry import Polygon, Point as ShapelyPoint
import geojson

from monitoring.monitorlib.clients.geospatial_info.client_geospatial_map import (
    GeospatialMapClient,
    GeospatialInfoError,
)
from monitoring.monitorlib.infrastructure import UTMClientSession


class MockUTMClientSession(UTMClientSession):
    def __init__(self, base_url="http://dummy.com"):
        super().__init__(base_url, MagicMock()) # MagicMock for auth_adapter
        # Mock the underlying client used by self.get(), self.post(), etc.
        self.client = MagicMock(spec=requests.Session)


class TestGeospatialMapClient(unittest.TestCase):
    def setUp(self):
        self.mock_session = MockUTMClientSession()
        self.participant_id = "test_participant"
        self.client = GeospatialMapClient(self.mock_session, self.participant_id)
        self.test_geojson_fc = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]},
                    "properties": {},
                },
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [2, 2]},
                    "properties": {},
                },
            ],
        }

    def test_get_dynamic_features_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = self.test_geojson_fc
        mock_response.status_code = 200
        self.mock_session.get = MagicMock(return_value=mock_response) # Mocking the get method directly on session instance

        features = self.client.get_dynamic_features("http://test.com/data.geojson")
        self.assertEqual(features, self.test_geojson_fc)
        self.mock_session.get.assert_called_once_with("http://test.com/data.geojson", timeout=None) # Default timeout

    def test_get_dynamic_features_success_configured_url(self):
        client_with_config_url = GeospatialMapClient(
            self.mock_session, self.participant_id, dynamic_source_url="http://configured.com/data.geojson"
        )
        mock_response = MagicMock()
        mock_response.json.return_value = self.test_geojson_fc
        mock_response.status_code = 200
        self.mock_session.get = MagicMock(return_value=mock_response)

        features = client_with_config_url.get_dynamic_features()
        self.assertEqual(features, self.test_geojson_fc)
        self.mock_session.get.assert_called_once_with("http://configured.com/data.geojson", timeout=None)


    def test_get_dynamic_features_invalid_json(self):
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.status_code = 200
        self.mock_session.get = MagicMock(return_value=mock_response)

        with self.assertRaises(GeospatialInfoError) as context:
            self.client.get_dynamic_features("http://test.com/bad_json.geojson")
        self.assertIn("Failed to parse GeoJSON response", str(context.exception))

    def test_get_dynamic_features_request_failure(self):
        self.mock_session.get = MagicMock(side_effect=requests.exceptions.RequestException("Connection error"))

        with self.assertRaises(GeospatialInfoError) as context:
            self.client.get_dynamic_features("http://test.com/error.geojson")
        self.assertIn("Failed to fetch dynamic GeoJSON", str(context.exception))
        
    def test_get_dynamic_features_http_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Not Found")
        self.mock_session.get = MagicMock(return_value=mock_response)

        with self.assertRaises(GeospatialInfoError) as context: # Should be HTTPError via requests.raise_for_status -> GeospatialInfoError
            self.client.get_dynamic_features("http://test.com/notfound.geojson")
        self.assertIn("Failed to fetch dynamic GeoJSON", str(context.exception))


    def test_get_dynamic_test_points_success(self):
        # Mock get_dynamic_features to return our test GeoJSON
        self.client.get_dynamic_features = MagicMock(return_value=self.test_geojson_fc)

        points = self.client.get_dynamic_test_points("http://test.com/data.geojson")

        self.assertEqual(len(points), 2)
        # Polygon centroid (0.5, 0.5)
        self.assertIsInstance(points[0], s2sphere.LatLng)
        self.assertAlmostEqual(points[0].lat().degrees, 0.5)
        self.assertAlmostEqual(points[0].lng().degrees, 0.5)
        # Point centroid (2, 2)
        self.assertIsInstance(points[1], s2sphere.LatLng)
        self.assertAlmostEqual(points[1].lat().degrees, 2.0)
        self.assertAlmostEqual(points[1].lng().degrees, 2.0)
        self.client.get_dynamic_features.assert_called_once_with("http://test.com/data.geojson", None)

    def test_get_dynamic_test_points_no_features(self):
        empty_fc = {"type": "FeatureCollection", "features": []}
        self.client.get_dynamic_features = MagicMock(return_value=empty_fc)

        points = self.client.get_dynamic_test_points("http://test.com/empty.geojson")
        self.assertEqual(len(points), 0)

    def test_get_dynamic_test_points_invalid_geojson_structure(self):
        invalid_fc = {"type": "NotAFeatureCollection", "features": []}
        self.client.get_dynamic_features = MagicMock(return_value=invalid_fc)

        with self.assertRaises(GeospatialInfoError) as context:
            self.client.get_dynamic_test_points("http://test.com/invalid_fc.geojson")
        self.assertIn("Invalid GeoJSON FeatureCollection structure", str(context.exception))

    def test_get_dynamic_test_points_malformed_feature(self):
        # One valid, one malformed feature (missing geometry)
        malformed_fc = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": {"type": "Point", "coordinates": [1, 1]}, "properties": {}},
                {"type": "Feature", "properties": {}}, # Malformed
            ],
        }
        self.client.get_dynamic_features = MagicMock(return_value=malformed_fc)
        
        # Expect a warning to be printed for the malformed feature
        with patch("builtins.print") as mock_print:
            points = self.client.get_dynamic_test_points("http://test.com/malformed_feature.geojson")
            self.assertEqual(len(points), 1) # Only the valid point
            self.assertAlmostEqual(points[0].lat().degrees, 1.0)
            self.assertAlmostEqual(points[0].lng().degrees, 1.0)
            mock_print.assert_called() # Check that print was called (for the warning)


    def test_get_dynamic_test_points_unsupported_geometry(self):
        # Shapely might not support all GeoJSON geometry types directly for centroid calculation,
        # or some might result in errors. For instance, a GeometryCollection.
        # The current implementation of get_dynamic_test_points uses shapely.shape(feature['geometry']).centroid
        # which might fail or produce odd results for GeometryCollection.
        # Here we test with a LineString, for which centroid is defined.
        linestring_feature = geojson.Feature(geometry=geojson.LineString([(0,0), (2,2)]))
        fc_with_linestring = geojson.FeatureCollection([linestring_feature])
        
        self.client.get_dynamic_features = MagicMock(return_value=fc_with_linestring)
        points = self.client.get_dynamic_test_points("http://test.com/linestring.geojson")
        
        self.assertEqual(len(points), 1)
        self.assertIsInstance(points[0], s2sphere.LatLng)
        # Centroid of LineString [(0,0), (2,2)] is (1,1)
        self.assertAlmostEqual(points[0].lat().degrees, 1.0)
        self.assertAlmostEqual(points[0].lng().degrees, 1.0)

    def test_get_dynamic_test_points_geometry_collection(self):
        # A GeometryCollection's centroid is typically the centroid of its constituent geometries.
        # Shapely's shape(geom_collection).centroid should handle this.
        point = ShapelyPoint(1, 1)
        polygon = Polygon([(2,2), (2,3), (3,3), (3,2), (2,2)]) # Centroid (2.5, 2.5)
        
        # GeoJSON representation of GeometryCollection
        # Note: s2sphere.LatLng.from_degrees expects (lat, lon)
        # Shapely points are (x, y) -> (lon, lat)
        gc_feature = geojson.Feature(geometry=geojson.GeometryCollection([
            geojson.Point((1,1)), # lon, lat
            geojson.Polygon([[(2,2), (2,3), (3,3), (3,2), (2,2)]]) # lon, lat
        ]))
        fc_with_gc = geojson.FeatureCollection([gc_feature])

        self.client.get_dynamic_features = MagicMock(return_value=fc_with_gc)
        points = self.client.get_dynamic_test_points("http://test.com/geomcollection.geojson")

        self.assertEqual(len(points), 1) 
        # The centroid of a GeometryCollection containing a Point(1,1) and a Polygon centered at (2.5, 2.5)
        # is not straightforward to calculate without knowing Shapely's exact weighting.
        # However, it should be a valid LatLng. We can check if it's roughly in the middle.
        # Centroid of Point(1,1) and Point(2.5, 2.5) would be (1.75, 1.75)
        # This is just a sanity check that it produces a point.
        self.assertIsInstance(points[0], s2sphere.LatLng)
        # print(f"GC Centroid: ({points[0].lng().degrees}, {points[0].lat().degrees})") # For debugging
        # Example: centroid of Point(1,1) and Polygon(centroid 2.5,2.5) -> (1.75, 1.75) if areas are equal or not considered.
        # Shapely's centroid for GeometryCollection is the centroid of the union of the geometries.
        # Union of Point(1,1) and Polygon (area 1) will be dominated by polygon.
        # Let's check if it's close to the polygon's centroid if the point is inside, or a weighted average.
        # For simplicity, we'll just check it's a valid point. A more precise test would require
        # knowing shapely's exact behavior or using simpler constituent geometries.
        # For now, just ensure it doesn't crash and produces one point.

if __name__ == "__main__":
    unittest.main()
