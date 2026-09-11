{
  /* Table of subfigure plots, one for each scenario, with successful flight throughput, failed
   * flight throughput, and operational intent creation latency.
   *   name: File name for artifact
   *   title: Title for overall subfigure table
   *   n_cols: Number of columns in the subfigure table
   *   n_scenarios: Total number of scenarios (maximum; incomplete test runs may have fewer)
   */
  throughput_latency_plots: function (name, title, n_cols, n_scenarios) {
    matplotlib_figure: {
      name: name,
      title: title,
      n_subfigure_rows: std.ceil(n_scenarios / n_cols),
      n_subfigure_cols: n_cols,
      evaluation_context: [
        {
          name: 'throughputs',
          value: '[[throughput_of_step(scenario, s, types=["workflow.flight_planner.flight"], outcomes=[True])' +
                '  for s in completed_step_indices(scenario.steps)]' +
                ' for scenario in report.report.scenarios]',
        },
        {
          name: 'latencies',
          value: '[[latency_of_step(scenario, s, types=["query.astm.f3548.v21.dss.createOperationalIntentReference"], outcomes=[True, False]).total_seconds() * 1000' +
                '  for s in completed_step_indices(scenario.steps)]' +
                ' for scenario in report.report.scenarios]',
        },
      ],
      subfigures: [
        {
          title_expr: 'report.report.scenarios[%d].name' % scenario_index,
          subplots: [
            {
              render_expr: '%d < len(report.report.scenarios)' % scenario_index,
              evaluation_context: [
                {
                  name: 'scenario',
                  value: 'report.report.scenarios[%d]' % scenario_index,
                },
                {
                  name: 'scale',
                  value: '[step.load_factor for step in completed_steps(scenario.steps)]',
                },
                {
                  name: 'failures',
                  value: '[throughput_of_step(scenario, s, types=["workflow.flight_planner.flight"], outcomes=[False])' +
                        ' for s in completed_step_indices(scenario.steps)]',
                },
                {
                  name: 'usl',
                  value: 'USLFit.from_data(scale, throughputs[%d])' % scenario_index,
                },
              ],
              x_axis: {
                label: 'Flight planners',
              },
              y_axis: {
                label: 'Throughput\n(Flights/s)',
                min_value: 0,
                max_value_expr: 'max(throughputs)',
              },
              y_axes: [
                {
                  label: 'Latency\n(Create ISA ms)',
                  min_value: 0,
                  max_value_expr: 'max(latencies)',
                },
              ],
              xy_plots: [
                {
                  type: 'Line',
                  color: 'lightgray',
                  label_expr: 'f"USL: $\\\\gamma$={usl.parameters.scaling_factor:.2g} $\\\\alpha$={usl.parameters.contention_factor:.2g} $\\\\beta$={usl.parameters.coherency_factor:.2g}"',
                  x_data_expr: 'scale',
                  y_data_expr: 'list(usl.compute_throughput(scale))',
                  kwargs: {
                    zorder: -1,
                  },
                },
                {
                  type: 'Scatter',
                  color: 'orange',
                  label_expr: '"Latency"',
                  x_data_expr: 'scale',
                  y_data_expr: 'latencies[%d]' % scenario_index,
                  y_axis: 1,
                  kwargs: {
                    zorder: -0.9,
                  },
                },
                {
                  type: 'Scatter',
                  color: 'green',
                  label_expr: '"Successes"',
                  x_data_expr: 'scale',
                  y_data_expr: 'throughputs[%d]' % scenario_index,
                },
                {
                  type: 'Scatter',
                  color: 'red',
                  label_expr: '"Failures"',
                  x_data_expr: 'scale',
                  y_data_expr: 'failures',
                },
              ],
              legend: {
                location: 'upper left',
                font_size: 'x-small',
                label_spacing: 0.2,
                border_padding: 0.2,
              },
            },
          ],
        } for scenario_index in std.range(0, n_scenarios - 1)
      ],
    },
  },

  /* Timeline of SCD flights including the entire flight and operational intent CRUD operations. */
  scd_flights_timeline: {
    timeline: {
      name: 'timeline',
      operations: [
        {
          type: "workflow.flight_planner.flight",
          color: "#32aced",
          success_indicator_width: 5,
        },
        {
          type: "query.astm.f3548.v21.dss.createOperationalIntentReference",
          color: "#c7c46b",
        },
        {
          type: "query.astm.f3548.v21.dss.updateOperationalIntentReference",
          color: "#70c76b",
        },
        {
          type: "query.astm.f3548.v21.dss.deleteOperationalIntentReference",
          color: "#c2c2c2",
        },
      ],
    }
  },
}
