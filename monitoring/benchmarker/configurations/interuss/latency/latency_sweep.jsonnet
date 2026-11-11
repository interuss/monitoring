/* Full inter-USS latency sweep; see latency_sweep.libsonnet. */

local loads = import '../loads.libsonnet';
local sweep = import './latency_sweep.libsonnet';

sweep(
  test_name='Inter-USS latency sweep',
  delays_ms=[0, 5, 10, 20, 30, 50],
  instances=[1, 2, 3],
  initial_users=4,
  isa_criteria={
    throughput_stability_criteria: {
      each_user_completed_at_least: { count: 1, operations: ['workflow.flight_planner.flight'] },
    },
    throughput_instability_criteria: {
      any_of: [
        { failures_more_than: { count: 5, operations: ['query.astm.f3411.v22a.dss.createIdentificationServiceArea'] } },
        { phase_duration_at_least: '60s' },
        { average_duration_more_than: { duration: '6s', operations: ['query.astm.f3411.v22a.dss.createIdentificationServiceArea'] } },
      ],
    },
    step_completion_criteria: {
      sampling_duration_at_least: '30s',
      completed_at_least: { count: 5, operations: ['workflow.flight_planner.flight'] },
    },
    max_users: 400,
  },
  scd_criteria={
    throughput_stability_criteria: loads.normal_flights_stability_criteria,
    throughput_instability_criteria: loads.normal_flights_instability_criteria,
    step_completion_criteria: loads.normal_flights_completion_criteria,
  },
  search_completion_criteria={
    adjacency_user_count: 2,
    consecutive_unstable_user_counts: 3,
    consecutive_stable_user_counts: 3,
    maximum_left_side_spacing: 0.2,
    max_throughput_adjacent_user_counts: 2,
  },
)
