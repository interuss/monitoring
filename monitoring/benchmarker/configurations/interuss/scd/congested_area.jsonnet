/* Dense/overlapping SCD flight operations applied to an existing DSS deployment after adding
 * subscriptions to intentionally cause contention.  Load applied to one DSS instance at a time to
 * separate the performance of addressing a leader or a follower.
 */

// Top-level constants
local test_name = 'Congested Area';
local num_uss = 3;
local num_nodes = 3;
local num_subscriptions = 8; // Should not exceed 10 because of how subscription IDs are constructed below
local initial_users = 3;
local lat_size = 0.00001;
local lng_size = 0.00001;

local scenarios = import './scenarios.libsonnet';
local users = import './users.libsonnet';
local s2_cell_of = std.native('s2.cell_of');
local s2_inscribed_latlng_rect = std.native('s2.inscribed_latlng_rect');
local rect = s2_inscribed_latlng_rect(s2_cell_of(34, -118, 13));

scenarios.flight_planner_search(
  test_name, num_nodes, initial_users,
  [
    [
      {
        name: 'FPU%d' % uss,
        flight_planner: users.basic_flight_planner(
          ['uss%d_dss_pool' % uss], '3bdb0b88-a522-4286-9499-060e56c953bb', rect, lat_size, lng_size
        ),
      },
    ] for uss in std.range(1, num_uss)
  ],
  [
    {
      id: '3bdb0b88-a522-4286-9499-%d60e56c953bb' % (sub_index - 1),
      rect: rect,
    } for sub_index in std.range(1, num_subscriptions)
  ],
)
