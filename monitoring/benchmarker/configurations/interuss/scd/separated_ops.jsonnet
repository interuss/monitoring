/* Widely separated SCD flight operations, corresponding to the intent of
 * "Global Throughput (Multi Site) Test Part 1":
 * https://github.com/interuss/dss/issues/1541#issuecomment-4846753840
 *
 * Distribute planners across 116 sites with one subscription and one OVN coordination
 * group per site.  Sites share neither subscriptions nor operational intents, while
 * planners at the same site still contend on its subscription and may overlap.
 * As in congested_area, load one DSS instance at a time, selecting its nodes randomly.
 */

local test_name = 'Separated Operations';
local num_uss = 3;
local num_nodes = 3;
local num_sites = 116;
local initial_users = 16;
local site_columns = 11;
local site_spacing_cells = 4;
local lat_size = 0.00001;
local lng_size = 0.00001;

local scenarios = import './scenarios.libsonnet';
local sites = import './sites.libsonnet';
local users = import './users.libsonnet';
local s2_cell_of = std.native('s2.cell_of');
// Level 11 gives each site a several-kilometer operating area.  Four-cell spacing
// leaves gaps between sites; S2 offsets avoid assuming a fixed km-per-degree scale.
local rects = sites.grid(s2_cell_of(34, -118, 11), num_sites, site_columns, site_spacing_cells);
local subscriptions = [
  {
    id: '48ff9727-d204-4cc3-9b7a-%012x' % i,
    rect: rects[i],
  } for i in std.range(0, num_sites - 1)
];

scenarios.flight_planner_search(
  test_name, num_nodes, initial_users,
  [
    [
      {
        name: 'FPU%d_s%d' % [uss, i + 1],
        flight_planner: users.basic_flight_planner(
          ['uss%d_dss_pool' % uss], subscriptions[i].id, rects[i], lat_size, lng_size,
          'site%d' % (i + 1),
        ),
      } for i in std.range(0, num_sites - 1)
    ] for uss in std.range(1, num_uss)
  ],
  subscriptions,
)
