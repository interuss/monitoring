/* Dense/overlapping SCD flight operations applied to an existing DSS deployment after adding
 * subscriptions to intentionally cause contention.  Load applied to one DSS instance at a time to
 * separate the performance of addressing a leader or a follower.
 */

local s2_cell_of = std.native('s2.cell_of');

// Top-level constants
local test_name = 'Congested Area';
local num_uss = 3;
local num_nodes = 3;
local num_subscriptions = 8; // Should not exceed 10 because of how subscription IDs are constructed below
local users_per_step = 3;
local s2cell = s2_cell_of(34, -118, 13);
local lat_size = 0.00001;
local lng_size = 0.00001;

// Imports and constructed values
local actions = import './actions.libsonnet';
local artifacts = import '../artifacts.libsonnet';
local environment = import './local_environment.libsonnet';
local flights = import '../flights.libsonnet';
local loads = import '../loads.libsonnet';
local users = import './users.libsonnet';
local s2_inscribed_latlng_rect = std.native('s2.inscribed_latlng_rect');
local s2_expand_latlng_rect = std.native('s2.expand_latlng_rect');
local rect = s2_inscribed_latlng_rect(s2cell);

{
  resources: {
    resource_declarations: {
      utm_auth: environment.dummy_oauth_resource_declaration,
    } + {
      ['uss%d_dss_pool' % uss]: environment.dss_instances_resource_declaration(
        std.range(uss - 1, uss - 1), std.range(0, num_nodes - 1), 'utm_auth'
      ) for uss in std.range(1, num_uss)
    },
  },

  actions: [
    {
      name: 'Generate intermediate artifacts',
      generate_artifacts: {
        subfolder: 'f"intermediate{action_invocation}"',
        defined_artifact_indices: [0, 1, 2],
      },
    },
  ] + [
    actions.create_subscription(
      'Create subscription %d' % sub_index,
      '3bdb0b88-a522-4286-9499-%d60e56c953bb' % (sub_index - 1),
      rect,
    ) for sub_index in std.range(1, num_subscriptions)
  ] + [
    {
      name: 'Delete subscription %d' % sub_index,
      f3548: {
        delete_subscription: {
          subscription_id: '3bdb0b88-a522-4286-9499-%d60e56c953bb' % (sub_index - 1),
          mode: 'GetDeleteIfExist',
        },
      },
    } for sub_index in std.range(1, num_subscriptions)
  ],

  user_types: [
    {
      name: 'FPU%d' % uss, // Flight planner user using DSS instance from uss
      flight_planner: {
        flight_generation: {
          independent_time_location_shape: {
            time: {
              fixed_spacing: '36s',
              uniform_random_spacing: '7.2s',
            },
            location: flights.laglng_rect_location(s2_expand_latlng_rect(rect, -lat_size, -lng_size)),
            shape: flights.latlng_rect_shape(lat_size, lng_size),
          },
        },
        flight_execution: {
          end_flight_after_start: '5s',
        },
        scd_behavior: users.basic_scd_behavior(['uss%d_dss_pool' % uss], '3bdb0b88-a522-4286-9499-060e56c953bb', '20s', '10s'),
      },
    } for uss in std.range(1, num_uss)
  ],

  loads: [
    {
      name: 'Flight planner ramp for USS %d' % uss,
      user_ramp: {
        user_type: 'FPU%d' % uss,
        initial_users: users_per_step,
        additional_users_per_step: users_per_step,
        random_seed: 1234,
        throughput_stability_criteria: loads.normal_flights_stability_criteria,
        throughput_instability_criteria: loads.normal_flights_instability_criteria,
        step_completion_criteria: loads.normal_flights_completion_criteria,
        load_completion_criteria: {
          any_of: [
            {
              throughput_lower_than_peak: {
                operations: ['workflow.flight_planner.flight'],
                fraction_of_peak: 0.7,
              },
            },
          ],
        },
      },
    } for uss in std.range(1, num_uss)
  ],

  scenarios: [
    {
      name: 'DSS instance %d' % uss,
      [if uss == 1 then "setup"]: ['Create subscription %d' % sub_index for sub_index in std.range(1, num_subscriptions)],
      load: 'Flight planner ramp for USS %d' % uss,
      teardown:
        (if uss < num_uss then ['Generate intermediate artifacts'] else [])
        + (if uss == num_uss then ['Delete subscription %d' % sub_index for sub_index in std.range(1, num_subscriptions)] else []),
    } for uss in std.range(1, num_uss)
  ],

  artifacts: [
    {
      raw_report: {
        name: 'report',
      },
    },
    artifacts.scd_flights_timeline,
    artifacts.throughput_latency_plots(
      'scalability_curve',
      test_name,
      num_uss,
      num_uss,
    ),
    {
      usslogset: {
        include_headers: ['Authorization'],
      },
    },
  ],
}
