{
  // throughput_stability_criteria for normal flights
  normal_flights_stability_criteria: {
    each_user_completed_at_least: {
      count: 1,
      operations: ['workflow.flight_planner.flight'],
    },
  },

  // throughput_instability_criteria for normal flights
  normal_flights_instability_criteria: {
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

  // step_completion_criteria for normal flights
  normal_flights_completion_criteria: {
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
}
