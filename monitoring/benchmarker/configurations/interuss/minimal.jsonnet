/* Minimal benchmarker scenario designed to run as quickly as practical while still exercising a
 * large proportion of benchmarker functionality.
 *
 * This is a smoke test, not a meaningful performance measurement.
 */

local artifacts = import './artifacts.libsonnet';
local subscription_ids = {
  f3411: 'e3429c02-d36f-4d8f-a589-e82a3461a528',
  f3548: 'c73c9430-f782-4d55-ad12-929ea9f626c7',
};
local subscription = {
  duration: '10m',
  area: { lat_min: 33.999, lng_min: -118.001, lat_max: 34.001, lng_max: -117.999 },
  min_alt: { value: 0, units: 'M', reference: 'W84' },
  max_alt: { value: 1000, units: 'M', reference: 'W84' },
};
local short_flights = {
  user_types: ['Shared subscription planner', 'Implicit subscription planner'],
  random_seed: 1234,
  throughput_stability_criteria: {
    each_user_completed_at_least: {
      count: 1,
      operations: ['workflow.flight_planner.flight'],
    },
  },
  throughput_instability_criteria: {
    any_of: [
      { phase_duration_at_least: '15s' },
      {
        failures_more_than: {
          count: 2,
          operations: ['workflow.flight_planner.flight'],
        },
      },
    ],
  },
  step_completion_criteria: {
    sampling_duration_at_least: '2s',
    completed_at_least: {
      count: 1,
      operations: ['workflow.flight_planner.flight'],
    },
  },
};

{
  resources: {
    resource_declarations: {
      utm_auth: {
        resource_type: 'resources.communications.AuthAdapterResource',
        specification: {
          auth_spec: 'DummyOAuth(http://localhost:8085/token,benchmarker)',
          scopes_authorized: [
            'utm.strategic_coordination',
            'rid.service_provider',
            'rid.display_provider',
          ],
        },
      },
      scd_dss: {
        resource_type: 'resources.astm.f3548.v21.DSSInstancesResource',
        dependencies: { auth_adapter: 'utm_auth' },
        specification: {
          dss_instances: [
            {
              participant_id: 'uss%d_dss1' % uss,
              base_url: 'http://localhost:800%d' % uss,
            } for uss in [1, 2]
          ],
        },
      },
      netrid_dss: {
        resource_type: 'resources.astm.f3411.DSSInstancesResource',
        dependencies: { auth_adapter: 'utm_auth' },
        specification: {
          dss_instances: [
            {
              participant_id: 'uss%d_dss1' % uss,
              base_url: 'http://localhost:800%d/rid/v2' % uss,
              rid_version: 'F3411-22a',
            } for uss in [1, 2]
          ],
        },
      },
    },
  },

  actions: [
    {
      name: 'Bring up DSS pool',
      run_command: {
        path: '$REPO_ROOT',
        command: 'make start-locally',
        env: {
          // One node per USS keeps startup small while exercising inter-USS replication.
          NUM_USS: '2',
          NUM_NODES: '1',
          DSS_IMAGE: 'interuss/dss:v0.23.0',
          DB_TYPE: 'crdb',
          INTRA_USS_NETEM_CONF: 'delay 600us 40us 25% distribution normal loss 0.0005%',
          INTER_USS_NETEM_CONF: 'delay 25ms 1.25ms 50% distribution paretonormal loss 0.25% 15%',
        },
      },
    },
    {
      name: 'Tear down DSS pool',
      run_command: {
        path: '$REPO_ROOT',
        command: 'make clean-locally',
        env: { NUM_USS: '2', NUM_NODES: '1', DB_TYPE: 'crdb' },
      },
    },
    {
      name: 'Generate intermediate artifacts',
      generate_artifacts: {
        subfolder: 'f"intermediate{action_invocation}"',
        defined_artifact_indices: [0, 1, 2, 3],
      },
    },
  ] + [
    {
      name: 'Create %s subscription' % protocol,
      [protocol]: {
        create_subscription: {
          subscription: subscription + {
            subscription_id: subscription_ids[protocol],
          } + (if protocol == 'f3411' then { rid_version: 'F3411-22a' } else {}),
          mode: 'GetDeleteCreate',
        },
      },
    } for protocol in ['f3411', 'f3548']
  ] + [
    {
      name: 'Delete %s subscription' % protocol,
      [protocol]: {
        delete_subscription: {
          subscription_id: subscription_ids[protocol],
          mode: 'GetDeleteIfExist',
        },
      },
    } for protocol in ['f3411', 'f3548']
  ],

  setup_actions: ['Bring up DSS pool'],
  // The engine runs this even if a scenario or its subscription cleanup fails.
  teardown_actions: ['Tear down DSS pool'],

  user_types: [
    {
      name: '%s subscription planner' % strategy,
      flight_planner: {
        flight_generation: {
          independent_time_location_shape: {
            time: { fixed_spacing: '2s', uniform_random_spacing: '0.2s' },
            location: {
              fixed_location: {
                horizontal: { lat: 34, lng: -118 },
                vertical: { value: 300, reference: 'W84', units: 'M' },
              },
            },
            shape: {
              fixed_volumes: {
                origin_horizontal: { lat: 0, lng: 0 },
                origin_vertical: { value: 0, reference: 'W84', units: 'M' },
                origin_time: '2026-01-01T00:00:00Z',
                volumes: [
                  {
                    volume: {
                      outline_polygon: {
                        vertices: [
                          { lat: -0.00001, lng: -0.00001 },
                          { lat: 0.00001, lng: -0.00001 },
                          { lat: 0.00001, lng: 0.00001 },
                          { lat: -0.00001, lng: 0.00001 },
                        ],
                      },
                      altitude_lower: { value: 0, reference: 'W84', units: 'M' },
                      altitude_upper: { value: 20, reference: 'W84', units: 'M' },
                    },
                    time_start: '2026-01-01T00:00:00Z',
                    time_end: '2026-01-01T00:00:02Z',
                  },
                ],
              },
            },
          },
          execution: { end_flight_after_start: '1s' },
        },
        scd_behavior: {
          dss_pool: ['scd_dss'],
          dss_selection_strategy: 'Random',
          subscription_strategy:
            if strategy == 'Shared' then {
              single_subscription: { subscription_id: subscription_ids.f3548 },
            } else {
              implicit_subscription: {},
            },
          op_intent_ref_creation_strategy: {
            ovn_coordination_group: 'minimal',
            coordinate_requested_ovns: true,
            retries: 2,
            accept_before_flight_start: '2s',
            activate_before_flight_start: '1s',
            // Short notice is intentional here; a busy development host may start late.
            expect_timely_clearance: false,
          },
          op_intent_ref_cleanup_strategy: { after_actual_flight_end: '0.1s' },
        },
        astm_netrid_behavior: {
          dss_pool: ['netrid_dss'],
          dss_selection_strategy: 'Random',
          rid_version: 'F3411-22a',
          isa_strategy: {
            isa_per_flight: { before_flight_start: '1s', after_flight_end: '0.1s' },
          },
        },
      },
    } for strategy in ['Shared', 'Implicit']
  ],

  loads: [
    {
      name: 'Short user ramp',
      user_ramp: short_flights + {
        initial_users: 1,
        additional_users_per_step: 1,
        load_completion_criteria: { completed_steps: 2 },
      },
    },
    {
      name: 'Short user search',
      user_search: short_flights + {
        initial_users: 4,
        // Gap filling never increases the largest measured user count: at most four steps.
        // After a successful four-user step, the next step uses two users, so excess users
        // must stop and clean up while the remaining users continue their workflows.
        search_completion_criteria: { maximum_left_side_spacing: 0.5 },
      },
    },
  ],

  scenarios: [
    {
      name: 'Mixed SCD and NetRID ramp',
      setup: ['Create f3411 subscription', 'Create f3548 subscription'],
      load: 'Short user ramp',
      record_query_details: true,
      teardown: ['Generate intermediate artifacts'],
    },
    {
      name: 'Mixed SCD and NetRID search',
      load: 'Short user search',
      record_query_details: true,
      teardown: ['Delete f3548 subscription', 'Delete f3411 subscription'],
    },
  ],

  artifacts: [
    { raw_report: { name: 'report' } },
    artifacts.scd_flights_timeline + {
      timeline+: {
        operations+: [
          { type: 'workflow.flight_planner.active_flight', color: '#116699' },
          { type: 'query.astm.f3411.v22a.dss.createIdentificationServiceArea', color: '#aa77cc' },
          { type: 'query.astm.f3411.v22a.dss.deleteIdentificationServiceArea', color: '#ddbbff' },
        ],
      },
    },
    {
      matplotlib_figure: {
        name: 'throughput_latency',
        title: 'Minimal mixed SCD and NetRID smoke test',
        n_subfigure_cols: 2,
        subfigures: [
          {
            title: ['User ramp', 'User search'][i],
            // Intermediate generation has only the first scenario available.
            render_expr: '%d < len(report.report.scenarios)' % i,
            evaluation_context: [
              { name: 'scenario', value: 'report.report.scenarios[%d]' % i },
              { name: 'indices', value: 'list(completed_step_indices(scenario.steps))' },
              { name: 'users', value: '[scenario.steps[s].load_factor for s in indices]' },
            ],
            subplots: [
              {
                x_axis: { label: 'Flight planners' },
                y_axis: { label: 'Flights/s', min_value: 0 },
                y_axes: [{ label: 'DSS create latency (ms)', min_value: 0 }],
                xy_plots: [
                  {
                    type: 'Line',
                    label_expr: '"Flights"',
                    x_data_expr: 'users',
                    y_data_expr: '[throughput_of_step(scenario, s, types=["workflow.flight_planner.flight"]) for s in indices]',
                    kwargs: { marker: 'o' },
                  },
                ] + [
                  {
                    type: 'Scatter',
                    label_expr: '"%s"' % series.label,
                    x_data_expr: 'users',
                    y_data_expr: '[latency_of_step(scenario, s, types=["%s"]).total_seconds() * 1000 for s in indices]' % series.operation,
                    y_axis: 1,
                  }
                  for series in [
                    { label: 'SCD', operation: 'query.astm.f3548.v21.dss.createOperationalIntentReference' },
                    { label: 'NetRID', operation: 'query.astm.f3411.v22a.dss.createIdentificationServiceArea' },
                  ]
                ],
                legend: { location: 'upper left', font_size: 'x-small' },
              },
            ],
          }
          for i in [0, 1]
        ],
      },
    },
    { usslogset: { include_headers: ['Authorization', 'Content-Type'] } },
  ],
}
