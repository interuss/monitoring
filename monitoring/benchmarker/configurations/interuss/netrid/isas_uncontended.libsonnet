/* Creates and deletes ISAs without any contention-causing subscriptions, applying load to one
 * DSS instance at a time.
 *
 * resources must declare utm_auth and dss_pool_<N> (1-based) for each of num_uss USSs.
 * variants is an array of {name, setup (optional), teardown (optional)}; for each variant, the
 * setup actions run before the first DSS instance, the teardown actions after the last.
 */

local users = import './users.libsonnet';

function(num_uss, resources, variants, actions=[]) {
  resources: resources,

  actions: actions,

  user_types: [
    {
      name: 'FPU%d' % uss, // Flight planner user, DSS instance/USS i
      flight_planner: users.basic_flight_planner(['dss_pool_%d' % uss]),
    } for uss in std.range(1, num_uss)
  ],

  loads: [
    {
      name: 'Flight planner ramp for DSS instance %d' % uss,
      user_search: {
        user_type: 'FPU%d' % uss,
        initial_users: 16,
        user_expansion_ratio: 2,
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
                count: 5,
                operations: ['query.astm.f3411.v22a.dss.createIdentificationServiceArea'],
              },
            },
            {
              phase_duration_at_least: '60s',
            },
            {
              average_duration_more_than: {
                duration: '3s',
                operations: ['query.astm.f3411.v22a.dss.createIdentificationServiceArea'],
              },
            },
          ],
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
          ],
          sampling_duration_at_least: '10s',
          completed_at_least: {
            count: 5,
            operations: ['workflow.flight_planner.flight'],
          }
        },
        search_completion_criteria: {
          adjacency_user_count: 2,
          consecutive_unstable_user_counts: 3,
          consecutive_stable_user_counts: 3,
          maximum_left_side_spacing: 0.2,
          max_throughput_adjacent_user_counts: 2,
        },
      },
    } for uss in std.range(1, num_uss)
  ],

  scenarios: std.flattenArrays([
    [
      {
        name: 'Instance %d %s' % [uss, variants[v].name],
        [if uss == 1 && std.objectHas(variants[v], 'setup') then "setup"]: variants[v].setup,
        load: 'Flight planner ramp for DSS instance %d' % uss,
        [if uss == num_uss && std.objectHas(variants[v], 'teardown') then "teardown"]: variants[v].teardown,
        metadata: {
          variant: v,
          dss_instance: uss,
        }
      } for uss in std.range(1, num_uss)
    ] for v in std.range(0, std.length(variants) - 1)
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
        local n_cols = std.min(std.length(variants), std.ceil(std.sqrt(std.length(variants) * aspect_ratio))),
        local n_rows = std.ceil(std.length(variants) / n_cols),

        name: 'throughput_with_latency',
        n_subfigure_cols: n_cols,
        n_subfigure_rows: n_rows,
        subfigures: [
          {
            title: variants[v].name,
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
                          'if s.metadata["variant"] == %(variant)d and s.metadata["dss_instance"] == %(uss)d' +
                        ']') %
                        {variant: v, uss: uss},
                      },
                      {
                        name: 'scale',
                        value: '[step.load_factor for step in completed_steps(scenarios[0].steps)]',
                      },
                      {
                        name: 'throughput',
                        value: '[throughput_of_step(scenarios[0], s, types=["workflow.flight_planner.flight"])' +
                               ' for s in completed_step_indices(scenarios[0].steps)]',
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
          } for v in std.range(0, std.length(variants) - 1)
        ],
      },
    },
  ],
}
