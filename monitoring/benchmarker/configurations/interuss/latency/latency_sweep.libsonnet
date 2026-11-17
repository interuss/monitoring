/* Sweep of synthetic inter-USS latency on a local 3 USS x 1 node CockroachDB DSS pool.
 *
 * For each one-way inter-USS netem delay (RTT between USSs is twice that delay), the pool is
 * brought up, then a user-count search is performed against each selected DSS instance for each
 * workload:
 *   * isa: F3411 ISA create/delete without subscription
 *   * isa_sub: same, with one F3411 subscription covering the ISAs (synchronized update)
 *   * scd: F3548 flights with one shared subscription and OVN coordination
 * No loss is injected, nor latency between a DSS instance and its own database node.
 */

local netrid_actions = import '../netrid/actions.libsonnet';
local netrid_users = import '../netrid/users.libsonnet';
local scd_actions = import '../scd/actions.libsonnet';
local scd_users = import '../scd/users.libsonnet';

local s2_cell_of = std.native('s2.cell_of');
local s2_inscribed_latlng_rect = std.native('s2.inscribed_latlng_rect');

local num_uss = 3;
local f3411_sub_id = 'b1a5e9c4-7f3d-4c2a-9e6b-5d8f0a1c2e3f';
local f3548_sub_id = '6e2d4f8a-1b3c-4d5e-8f9a-0b1c2d3e4f5a';
local scd_rect = s2_inscribed_latlng_rect(s2_cell_of(34, -118, 13));
local isa_op = 'query.astm.f3411.v22a.dss.createIdentificationServiceArea';
local oir_op = 'query.astm.f3548.v21.dss.createOperationalIntentReference';
local blues = ['#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#08519c', '#08306b'];
local instance_colors = ['tab:blue', 'tab:orange', 'tab:green'];

local workloads = [
  { key: 'isa', label: 'ISA', op: isa_op, load: 'ISA', setup: [] },
  { key: 'isa_sub', label: 'ISA + 1 subscription', op: isa_op, load: 'ISA', setup: ['Create F3411 subscription'] },
  { key: 'scd', label: 'SCD', op: oir_op, load: 'SCD', setup: ['Create F3548 subscription'] },
];

local netem = function(delay_ms) 'delay %dms' % delay_ms;

local pool_env = { NUM_USS: std.toString(num_uss), NUM_NODES: '1', DB_TYPE: 'crdb' };

local scenarios_of = function(wl, inst) '[s for s in report.report.scenarios if s.metadata["workload"] == "%s" and s.metadata["dss_instance"] == %d and list(completed_step_indices(s.steps))]' % [wl, inst];

local curve_of = function(wl, inst, delay_ms) '[s for s in report.report.scenarios if s.metadata["workload"] == "%(wl)s" and s.metadata["dss_instance"] == %(inst)d and s.metadata["delay_ms"] == %(d)d]' % { wl: wl, inst: inst, d: delay_ms };

function(test_name, delays_ms, instances, initial_users, isa_criteria, scd_criteria, search_completion_criteria)
  local n_wl = std.length(workloads);
  local n_inst = std.length(instances);
  local color_of = function(k) blues[if std.length(delays_ms) == 1 then 5 else std.floor(k * 5 / (std.length(delays_ms) - 1))];
  local last_scenario = { wl: workloads[n_wl - 1].key, inst: instances[n_inst - 1] };
  {
    resources: {
      resource_declarations: {
        utm_auth: {
          resource_type: 'resources.communications.AuthAdapterResource',
          specification: {
            auth_spec: 'DummyOAuth(http://localhost:8085/token,benchmarker)',
            scopes_authorized: ['rid.service_provider', 'rid.display_provider', 'utm.strategic_coordination'],
          },
        },
      } + {
        ['f3411_dss_%d' % uss]: {
          resource_type: 'resources.astm.f3411.DSSInstancesResource',
          dependencies: { auth_adapter: 'utm_auth' },
          specification: {
            dss_instances: [{
              participant_id: 'uss%d_dss1' % uss,
              base_url: 'http://localhost:80%02d/rid/v2' % uss,
              rid_version: 'F3411-22a',
            }],
          },
        } for uss in std.range(1, num_uss)
      } + {
        ['f3548_dss_%d' % uss]: {
          resource_type: 'resources.astm.f3548.v21.DSSInstancesResource',
          dependencies: { auth_adapter: 'utm_auth' },
          specification: {
            dss_instances: [{
              participant_id: 'uss%d_dss1' % uss,
              base_url: 'http://localhost:80%02d' % uss,
            }],
          },
        } for uss in std.range(1, num_uss)
      },
    },

    actions: [
      {
        name: 'Bring up DSS pool: %dms delay' % delay_ms,
        run_command: {
          path: '$REPO_ROOT',
          command: 'make start-locally',
          env: pool_env + {
            DSS_IMAGE: 'interuss/dss:v0.23.0',
            INTRA_USS_NETEM_CONF: 'delay 0ms',
            INTER_USS_NETEM_CONF: netem(delay_ms),
          },
        },
      } for delay_ms in delays_ms
    ] + [
      {
        name: 'Tear down DSS pool',
        run_command: {
          path: '$REPO_ROOT',
          command: 'make clean-locally',
          env: pool_env,
        },
      },
      {
        name: 'Generate intermediate artifacts',
        generate_artifacts: {
          subfolder: 'f"intermediate{action_invocation}"',
          defined_artifact_indices: [1, 2, 3],
        },
      },
      netrid_actions.create_subscription('Create F3411 subscription', f3411_sub_id),
      scd_actions.create_subscription('Create F3548 subscription', f3548_sub_id, scd_rect),
    ],

    teardown_actions: ['Tear down DSS pool'],

    user_types: [
      {
        name: 'ISA_FPU%d' % uss,
        flight_planner: netrid_users.basic_flight_planner(['f3411_dss_%d' % uss], '5s'),
      } for uss in std.range(1, num_uss)
    ] + [
      {
        name: 'SCD_FPU%d' % uss,
        flight_planner: scd_users.basic_flight_planner(['f3548_dss_%d' % uss], f3548_sub_id, scd_rect, 0.00001, 0.00001),
      } for uss in std.range(1, num_uss)
    ],

    loads: [
      {
        name: '%s search for DSS instance %d' % [kind.name, uss],
        user_search: kind.criteria + {
          user_type: '%s_FPU%d' % [kind.name, uss],
          initial_users: initial_users,
          user_expansion_ratio: 2,
          random_seed: 1234,
          search_completion_criteria: search_completion_criteria,
          skip_unsatisfiable_criteria: true,
        },
      }
      for kind in [{ name: 'ISA', criteria: isa_criteria }, { name: 'SCD', criteria: scd_criteria }]
      for uss in std.range(1, num_uss)
    ],

    scenarios: [
      {
        local first = wl.key == workloads[0].key && inst == instances[0],
        local last = wl.key == last_scenario.wl && inst == last_scenario.inst,
        name: 'RTT %dms, %s, DSS instance %d' % [2 * delay_ms, wl.label, inst],
        setup: (if first then ['Bring up DSS pool: %dms delay' % delay_ms] else [])
               + (if inst == instances[0] then wl.setup else []),
        load: '%s search for DSS instance %d' % [wl.load, inst],
        teardown: if last then ['Tear down DSS pool', 'Generate intermediate artifacts'] else [],
        metadata: {
          delay_ms: delay_ms,
          rtt_ms: 2 * delay_ms,
          workload: wl.key,
          dss_instance: inst,
        },
      }
      for delay_ms in delays_ms
      for wl in workloads
      for inst in instances
    ],

    artifacts: [
      { raw_report: { name: 'report' } },
      {
        matplotlib_figure: {
          name: 'by_latency',
          title: test_name,
          n_subfigure_cols: n_wl,
          subfigures: [
            {
              title: wl.label,
              n_subplot_rows: 2,
              subplots: [
                {
                  x_axis: { label: 'Inter-USS RTT (ms)' },
                  y_axis: { label: metric.label, min_value: 0 },
                  xy_plots: [
                    {
                      type: 'Line',
                      color: instance_colors[inst - 1],
                      label_expr: '"DSS %d%s"' % [inst, series.suffix],
                      evaluation_context: [
                        { name: 'sc', value: scenarios_of(wl.key, inst) },
                        {
                          name: 'light',
                          value: '[sorted([(s.steps[i].load_factor, i) for i in completed_step_indices(s.steps)])[0][1] for s in sc]',
                        },
                        {
                          name: 'durations',
                          value: ('[sorted([(o.t1.datetime - o.t0.datetime).total_seconds() * 1000'
                                  + ' for o in select_operations(s.operations, types=["%s"], outcomes=[True],'
                                  + ' completed_after=s.steps[i].throughput_stability_time.datetime,'
                                  + ' completed_before=s.steps[i].end_time.datetime)])'
                                  + ' for s, i in zip(sc, light)]') % wl.op,
                        },
                        {
                          name: 'throughputs',
                          value: '[[(s.steps[i].load_factor, throughput_of_step(s, i, types=["workflow.flight_planner.flight"])) for i in completed_step_indices(s.steps)] for s in sc]',
                        },
                      ],
                      render_expr: 'sc',
                      x_data_expr: '[s.metadata["rtt_ms"] for s in sc]',
                      y_data_expr: series.expr,
                      kwargs: { marker: 'o', linestyle: series.linestyle },
                    }
                    for inst in instances
                    for series in metric.series
                  ],
                  legend: { location: 'best', font_size: 'x-small' },
                }
                for metric in [
                  {
                    key: 'peak',
                    label: 'Peak throughput\n(flights/s)',
                    series: [{ suffix: '', linestyle: '-', expr: '[max([p[1] for p in t]) for t in throughputs]' }],
                  },
                  {
                    key: 'latency',
                    label: 'Latency at lowest load\n(ms)',
                    series: [
                      { suffix: ' p50', linestyle: '-', expr: '[d[int(0.5 * (len(d) - 1))] if d else 0 for d in durations]' },
                      { suffix: ' p95', linestyle: '--', expr: '[d[int(0.95 * (len(d) - 1))] if d else 0 for d in durations]' },
                    ],
                  },
                ]
              ],
            }
            for wl in workloads
          ],
        },
      },
    ] + [
      {
        matplotlib_figure: {
          name: fig.name,
          title: test_name,
          n_subfigure_rows: n_wl,
          subfigures: [
            {
              title: wl.label,
              n_subplot_cols: n_inst,
              subplots: [
                {
                  title: 'DSS instance %d' % inst,
                  x_axis: { label: 'Flight planners' },
                  y_axis: { label: fig.y_label, min_value: 0 },
                  xy_plots: [
                    {
                      type: 'Line',
                      color: color_of(k),
                      label_expr: '"RTT %dms"' % (2 * delays_ms[k]),
                      evaluation_context: [
                        { name: 'sc', value: curve_of(wl.key, inst, delays_ms[k]) },
                        {
                          name: 'pts',
                          value: 'sorted([(sc[0].steps[i].load_factor, ' + std.strReplace(fig.y_expr, 'OP', wl.op) + ')'
                                 + ' for i in completed_step_indices(sc[0].steps)]) if sc else []',
                        },
                      ],
                      render_expr: 'pts',
                      x_data_expr: '[p[0] for p in pts]',
                      y_data_expr: '[p[1] for p in pts]',
                      kwargs: { marker: 'o' },
                    }
                    for k in std.range(0, std.length(delays_ms) - 1)
                  ],
                  legend: { location: 'best', font_size: 'x-small' },
                }
                for inst in instances
              ],
            }
            for wl in workloads
          ],
        },
      }
      for fig in [
        {
          name: 'throughput_by_users',
          y_label: 'Throughput\n(flights/s)',
          y_expr: 'throughput_of_step(sc[0], i, types=["workflow.flight_planner.flight"])',
        },
        {
          name: 'latency_by_users',
          y_label: 'Mean latency of key query\n(ms)',
          y_expr: 'latency_of_step(sc[0], i, types=["OP"]).total_seconds() * 1000',
        },
      ]
    ],
  }
