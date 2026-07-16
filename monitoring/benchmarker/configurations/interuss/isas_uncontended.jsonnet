local num_uss = 3;
local num_nodes = 3;
local latencies_ms = [std.max(1, i * 25) for i in std.range(0, 2)];
local jitter_frac = 0.05;

local nodeIndex = function(uss, node) std.format('%02d', node + num_nodes * (uss - 1));

{
  resources: {
    resource_declarations: {
      utm_auth: {
        resource_type: 'resources.communications.AuthAdapterResource',
        specification: {
          auth_spec: 'DummyOAuth(http://localhost:8085/token,benchmarker)',
          scopes_authorized: [
            'rid.service_provider',
            'rid.display_provider',
          ],
        },
      },
    } + {
      ["dss_pool_%d" % uss]: {
        resource_type: 'resources.astm.f3411.DSSInstancesResource',
        dependencies: {
          auth_adapter: 'utm_auth',
        },
        specification: {
          dss_instances: [
            {
              participant_id: 'uss%(uss)d_dss%(node)d' % { uss: uss, node: node },
              base_url: 'http://localhost:80%s/rid/v2' % nodeIndex(uss, node),
              rid_version: 'F3411-22a',
            } for node in std.range(1, num_nodes)
          ],
        },
      } for uss in std.range(1, num_uss)
    },
  },

  actions: [
    {
      name: 'Bring up DSS pool: %(latency)dms latency' % { latency: latency_ms },
      run_command: {
        env: {
          NUM_USS: std.toString(num_uss),
          NUM_NODES: std.toString(num_nodes),
          DSS_IMAGE: 'interuss/dss:v0.22.0',
          DB_TYPE: 'crdb',
          INTRA_USS_NETEM_CONF: 'delay 600us 40us 25% distribution normal loss 0.0005%',
          INTER_USS_NETEM_CONF: 'delay %(latency)sms %(jitter)sms 50%% distribution paretonormal loss 0.25%% 15%%' % { latency: latency_ms, jitter: latency_ms * jitter_frac },
        },
        path: '$REPO_ROOT',
        command: 'make start-locally',
      },
    }
    for latency_ms in latencies_ms
  ] + [
    {
      name: 'Tear down DSS pool',
      run_command: {
        env: {
          NUM_USS: std.toString(num_uss),
          NUM_NODES: std.toString(num_nodes),
          DB_TYPE: 'crdb',
        },
        path: '$REPO_ROOT',
        command: 'make clean-locally',
      },
    }
  ],

  user_types: [
    {
      name: 'FPU%d' % uss, // Flight planner user, DSS instance/USS i
      flight_planner: {
        flight_generation: {
          independent_time_location_shape: {
            time: {
              fixed_spacing: '0s',
            },
            location: {
              fixed_location: {
                horizontal: {lat: 34, lng: -118},
                vertical: {value: 300, reference: 'W84', units: 'M'},
              },
            },
            shape: {
              fixed_volumes: {
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
              },
            },
          },
        },
        astm_netrid_behavior: {
          rid_version: 'F3411-22a',
          dss_pool: ['dss_pool_%d' % uss],
          dss_selection_strategy: 'Random',
          isa_strategy: {
            isa_per_flight: {
              before_flight_start: '0s',
              after_flight_end: '2s',
            },
          },
        },
      },
    } for uss in std.range(1, num_uss)
  ],

  loads: [
    {
      name: 'Flight planner ramp for DSS instance %d' % uss,
      user_ramp: {
        user_type: 'FPU%d' % uss,
        initial_users: 10,
        additional_users_per_step: 10,
        throughput_stability_criteria: {
          each_user_completed_at_least: {
            count: 1,
            operations: ['workflow.flight_planner.flight'],
          },
        },
        step_completion_criteria: {
          any_of: [
            {
              sampling_duration_at_least: '30s',
            },
            {
              completed_at_least: {
                count: 100,
                operations: ['workflow.flight_planner.flight'],
              },
            },
            {
              average_duration_more_than: {
                duration: '20s',
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
            {
              failures_more_than: {
                count: 10,
                operations: ['workflow.flight_planner.flight'],
              }
            },
            {
              most_recent_step: {
                average_duration_more_than: {
                  duration: '20s',
                  operations: ['workflow.flight_planner.flight'],
                },
              },
            },
            {
              most_recent_step: {
                throughput_stability_took_longer_than: '30s',
              },
            },
          ],
        },
      },
    } for uss in std.range(1, num_uss)
  ],

  scenarios: std.flattenArrays([
    [
      {
        name: 'Instance %(uss)d %(latency)dms internode latency' % { uss: uss, latency: latency_ms },
        [if uss == 1 then "setup"]: ['Bring up DSS pool: %dms latency' % latency_ms],
        load: 'Flight planner ramp for DSS instance %d' % uss,
        [if uss == num_uss then "teardown"]: ['Tear down DSS pool'],
        metadata: {
          latency_ms: latency_ms,
          dss_instance: uss,
        }
      } for uss in std.range(1, num_uss)
    ] for latency_ms in latencies_ms
  ]),

  artifacts: [
    {
      raw_report: {
        name: 'report',
      },
    },
    {
      matplotlib_figure: {
        local aspect_ratio = 16 / 9,
        local n_cols = std.ceil(std.sqrt(std.length(latencies_ms) * aspect_ratio)),
        local n_rows = std.ceil(std.length(latencies_ms) / n_cols),

        name: 'throughput_with_latency',
        n_subfigure_cols: n_cols,
        n_subfigure_rows: n_rows,
        subfigures: [
          {
            title: '%dms internode latency' % latency_ms,
            subplots: [
              {
                x_axis: {
                  label: 'Flight planners',
                },
                y_axis: {
                  label: 'Throughput\n(Flights/s)',
                },
                xy_plots: [
                  {
                    type: 'Scatter',
                    label_expr: '"DSS %d"' % uss,
                    evaluation_context: [
                      {
                        name: 'scenarios',
                        value: ('[' +
                          's for s in report.report.scenarios ' +
                          'if s.metadata["latency_ms"] == %(latency)d and s.metadata["dss_instance"] == %(uss)d' +
                        ']') %
                        {latency: latency_ms, uss: uss},
                      },
                      {
                        name: 'scale',
                        value: '[step.load_factor for step in scenarios[0].steps]',
                      },
                      {
                        name: 'throughput',
                        value: '[throughput_of_step(scenarios[0], s, types=["workflow.flight_planner.flight"])' +
                               ' for s in range(len(scenarios[0].steps))]',
                      },
                    ],
                    render_expr: 'scenarios',
                    x_data_expr: 'scale',
                    y_data_expr: 'throughput',
                  } for uss in std.range(1, num_uss)
                ],
                legend: {
                  location: 'upper left',
                  font_size: 'x-small',
                  label_spacing: 0.2,
                  border_padding: 0.2,
                },
              }
            ],
          } for latency_ms in latencies_ms
        ],
      },
    },
  ],
}
