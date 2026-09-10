/* Dense/overlapping SCD flight operations applied to an existing DSS deployment after adding
 * subscriptions to cause maximum contention.
 */

local test_name = 'Single S2 cell';
local num_uss = 3;
local num_nodes = 3;
local num_subscriptions = 8;
local users_per_step = 3;

local artifacts = import '../artifacts.libsonnet';

local location = {
  uniform_box: {lat_min: 34, lat_max: 34.001, lng_max: -118, lng_min: -118.001},
  vertical: {value: 300, reference: 'W84', units: 'M'},
};

local shape = {
  origin_horizontal: {lat: 0, lng: 0},
  origin_vertical: {value: 0, reference: 'W84', units: 'M'},
  origin_time: '2026-01-01T00:00:00Z',
  volumes: [
    {
      volume: {
        outline_polygon: {
          vertices: [
            {lat: -0.00001, lng: -0.00001},
            {lat: 0.00001, lng: -0.00001},
            {lat: 0.00001, lng: 0.00001},
            {lat: -0.00001, lng: 0.00001},
          ],
        },
        altitude_lower: {value: 0, reference: 'W84', units: 'M'},
        altitude_upper: {value: 20, reference: 'W84', units: 'M'},
      },
      time_start: '2026-01-01T00:00:00Z',
      time_end: '2026-01-01T00:00:05Z',
    },
  ],
};

{
  resources: {
    local nodeIndex = function(uss, node) std.format('%02d', node + num_nodes * (uss - 1)),
    resource_declarations: {
      utm_auth: {
        resource_type: 'resources.communications.AuthAdapterResource',
        specification: {
          auth_spec: 'DummyOAuth(http://localhost:8085/token,benchmarker)',
          scopes_authorized: [
            'utm.strategic_coordination',
          ],
        },
      },
    } + {
      ['uss%d_dss_pool' % uss]: {
        resource_type: 'resources.astm.f3548.v21.DSSInstancesResource',
        dependencies: {
          auth_adapter: 'utm_auth',
        },
        specification: {
          dss_instances: [
            {
              participant_id: 'uss%(uss)d_dss%(node)d' % { uss: uss, node: node },
              base_url: 'http://localhost:80%s' % nodeIndex(uss, node),
            } for node in std.range(1, num_nodes)
          ],
        },
      } for uss in std.range(1, num_uss)
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
    {
      name: 'Create subscription %d' % sub_index,
      f3548: {
        create_subscription: {
          subscription: {
            subscription_id: '3bdb0b88-a522-4286-9499-%d60e56c953bb' % (sub_index - 1),
            duration: '23h',
            area: {
              lat_min: 34 - 0.00001,
              lng_min: -118.001 - 0.00001,
              lat_max: 34.001 + 0.00001,
              lng_max: -118 + 0.00001,
            },
            min_alt: {value: 0, units: 'M', reference: 'W84'},
            max_alt: {value: 3000, units: 'M', reference: 'W84'},
          },
          mode: 'GetDeleteCreate',
        },
      },
    } for sub_index in std.range(1, num_subscriptions)
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
            location: {
              random_location: location,
            },
            shape: {
                fixed_volumes: shape,
            },
          },
        },
        flight_execution: {
          end_flight_after_start: '5s',
        },
        scd_behavior: {
          dss_pool: ['uss%d_dss_pool' % uss],
          dss_selection_strategy: 'Random',
          subscription_strategy: {
            single_subscription: {
              subscription_id: '3bdb0b88-a522-4286-9499-060e56c953bb',
            },
          },
          op_intent_ref_creation_strategy: {
            ovn_coordination_group: 'cluster1',
            coordinate_requested_ovns: true,
            retries: 2,
            accept_before_flight_start: '20s',
            activate_before_flight_start: '10s',
            expect_timely_clearance: true,
          },
          op_intent_ref_cleanup_strategy: {
            after_actual_flight_end: '1s',
          },
        },
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
        throughput_stability_criteria: {
          each_user_completed_at_least: {
            count: 1,
            operations: ['workflow.flight_planner.flight'],
          },
        },
        throughput_instability_criteria: {
          any_of: [
            {
              failures_more_than: {
                count: 30,
                operations: ['workflow.flight_planner.flight'],
              },
            },
            {
              phase_duration_at_least: '120s',
            },
            {
              average_duration_more_than: {
                duration: '60s',
                operations: ['workflow.flight_planner.flight'],
              },
            },
          ],
        },
        step_completion_criteria: {
          any_of: [
            {
              sampling_duration_at_least: '90s',
            },
            {
              completed_at_least: {
                count: 100,
                operations: ['workflow.flight_planner.flight'],
              },
            },
          ],
          sampling_duration_at_least: '10s',
          completed_at_least: {
            count: 5,
            operations: ['workflow.flight_planner.flight'],
          }
        },
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
  ],
}
