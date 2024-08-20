{
  // ID of participant
  participant_id: 'uss2',

  // Set of requirements this participant wants to satisfy
  participant_requirements: 'Basic SCD without DSS provision',

  // (optional) IDs of subparticipants that make up this participant
  aggregate_participant_ids: [
    'uss2_core',
    'uss2_dss',
  ],

  // Definition of this participant's systems in the local environment
  local_env: {
    // (optional) Means by which to interact with the participant as a flight planner
    flight_planner: {
      participant_id: 'uss2_core',
      v1_base_url: 'http://scdsc.uss2.localutm/flight_planning/v1',
    },

    // (optional) Means by which to obtain this participant's software version in the test environment
    test_env_version_provider: {
      participant_id: 'uss2_core',
      interuss: {
        base_url: 'http://scdsc.uss2.localutm/versioning',
      },
    },

    // (optional) Means by which to obtain this participant's software version in the prod environment
    prod_env_version_provider: {
      participant_id: 'uss2_core',
      interuss: {
        base_url: 'http://scdsc.uss2.localutm/versioning',
      },
    },

    // (optional) List of DSS instances hosted by this participant
    dss_instances: [
      {
        participant_id: 'uss2_dss',
        base_url: 'http://dss.uss2.localutm',
      },
    ]
  }
}
