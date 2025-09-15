{
  // ID of participant
  participant_id: 'mock_uss',

  // Definition of this participant's systems in the local environment
  local_env: {
    // Base URL for all applicable APIs (note: only applicable for a mock_uss participant)
    mock_uss_base_url: 'http://scdsc.log.uss6.localutm',

    // (optional) Means by which to interact with the participant as a flight planner
    flight_planner: {
      participant_id: 'mock_uss',
      v1_base_url: 'http://scdsc.log.uss6.localutm/flight_planning/v1',
    },

    // (optional) Means by which to obtain this participant's software version in the test environment
    test_env_version_provider: {
      participant_id: 'uss1_core',
      interuss: {
        base_url: 'http://scdsc.log.uss6.localutm/versioning',
      },
    },
  }
}
