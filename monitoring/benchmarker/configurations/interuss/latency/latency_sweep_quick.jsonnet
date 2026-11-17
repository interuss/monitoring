/* Quick functional check of latency_sweep.jsonnet: 2 latencies, 2 DSS instances, few short steps.
 * Not a meaningful performance measurement.
 */

local sweep = import './latency_sweep.libsonnet';

local stability = {
  each_user_completed_at_least: { count: 1, operations: ['workflow.flight_planner.flight'] },
};

sweep(
  test_name='Inter-USS latency sweep (quick)',
  delays_ms=[0, 25],
  instances=[1, 2],
  initial_users=2,
  isa_criteria={
    throughput_stability_criteria: stability,
    throughput_instability_criteria: {
      any_of: [
        { phase_duration_at_least: '30s' },
        { failures_more_than: { count: 2, operations: ['workflow.flight_planner.flight'] } },
      ],
    },
    step_completion_criteria: {
      sampling_duration_at_least: '5s',
      completed_at_least: { count: 1, operations: ['workflow.flight_planner.flight'] },
    },
  },
  scd_criteria={
    throughput_stability_criteria: stability,
    throughput_instability_criteria: {
      any_of: [
        { phase_duration_at_least: '120s' },
        { failures_more_than: { count: 2, operations: ['workflow.flight_planner.flight'] } },
      ],
    },
    step_completion_criteria: {
      sampling_duration_at_least: '5s',
      completed_at_least: { count: 1, operations: ['workflow.flight_planner.flight'] },
    },
  },
  search_completion_criteria={ maximum_left_side_spacing: 0.5 },
)
