/* SCD flight operations concentrated into a smaller set of busy regions, corresponding
 * to the intent of "Global Throughput (Multi Site) Test Part 2":
 * https://github.com/interuss/dss/issues/1541#issuecomment-4846753840
 *
 * Distribute planners across 11 regions, each with one subscription and one OVN
 * coordination group.  At the same total user count, more planners share each
 * subscription than in separated_ops, increasing contention within regions while
 * operations in different regions remain independent.
 *
 * Larger regions reflect Part 2's larger operating radius.  As in the other SCD
 * configurations, load one DSS instance at a time, selecting its nodes randomly.
 */

local test_name = 'Typical Load';
local num_uss = 3;
local num_nodes = 3;
local num_sites = 11;
local initial_users = 16;
local site_columns = 4;
local site_spacing_cells = 4;
local lat_size = 0.00001;
local lng_size = 0.00001;

local scenarios = import './scenarios.libsonnet';
local sites = import './sites.libsonnet';
local s2_cell_of = std.native('s2.cell_of');
// Level 9 regions are approximately four times wider than separated_ops' level 11
// sites.  Each spans many level 13 cells; four-cell spacing leaves gaps between regions.
local rects = sites.grid(s2_cell_of(34, -118, 9), num_sites, site_columns, site_spacing_cells);

scenarios.multi_site_flight_planner_search(
  test_name, num_uss, num_nodes, initial_users, rects,
  'dc40cd82-31dd-4cc1-b21e-', lat_size, lng_size,
)
