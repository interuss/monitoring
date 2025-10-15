// Translates "incidents" GeoJSON provided via "geojson_example" external variable into a FeatureCheckTable
local features = std.extVar("geojson_example")["incidents"]["features"];
local timestamp_of = std.native("timestamp_of");
local now = timestamp_of("2025-10-11T13:30:08.503557+09:30");
local no_older_than = 24 * 60 * 60;

local make_row = function(index, feature, volumes)
  if feature["properties"]["_status"] == "closed" then
    null
  else if now - timestamp_of(feature["properties"]["_lastupdate"]) > no_older_than then
    null
  else
    {
      geospatial_check_id: "TEST_" + std.format("%03d", index + 1),
      requirement_ids: ["REQ_002"],
      description: feature["properties"]["_category"] + " at " + feature["properties"]["_datenotified"],
      operation_rule_set: "Rules1",
      restriction_source: "ThisRegulator",
      expected_result: "Block",
      volumes: volumes
    };

local make_4d_volume = function(footprint)
  footprint + {
    altitude_lower: {value: 0, units: "M", reference: "SFC"},
    altitude_upper: {value: 100, units: "M", reference: "SFC"},
    start_time: {time_during_test: "StartOfTestRun"},
    end_time: {
      offset_from: {
        starting_from: {time_during_test: "StartOfTestRun"},
        offset: "1h"
      }
    }
  };

local make_point_row = function(index, feature)
  local footprint = {
    outline_circle: {
      center: {
        lat: feature["geometry"]["coordinates"][1],
        lng: feature["geometry"]["coordinates"][0]
      },
      radius: {value: 10, units: "M"}
    },
  };
  local volumes = [make_4d_volume(footprint)];
  make_row(index, feature, volumes);

local make_polygon_row = function(index, feature)
  local footprint = {
    outline_polygon: {
      vertices: [
        {lng: coords[0], lat: coords[1]}
        for coords in feature["geometry"]["coordinates"][0]
      ]
    }
  };
  local volumes = [make_4d_volume(footprint)];
  make_row(index, feature, volumes);

local append_row = function(rows, feature)
  local new_row =
    if feature["geometry"]["type"] == "Point" then
      make_point_row(std.length(rows), feature)
    else if feature["geometry"]["type"] == "Polygon" then
      make_polygon_row(std.length(rows), feature)
    else
      null;
  if new_row == null then
    rows
  else
    rows + [new_row];

{
  rows: std.foldl(append_row, features, [])
}
