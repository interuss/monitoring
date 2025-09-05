{
  // ID of participant
  participant_id: 'uss1',

  // Set of requirements this participant wants to satisfy
  participant_requirements: 'Basic SCD',

  // (optional) IDs of subparticipants that make up this participant
  aggregate_participant_ids: [
    'uss1_core',
    'uss1_dss',
  ],

  // Definition of this participant's systems in the local environment
  local_env: {
    // The names of the tests in this environment in which this participant is participating
    participating_in_tests: ['test_1', 'test_2'],

    // (optional) Means by which to interact with the participant as a flight planner
    flight_planner: {
      participant_id: 'uss1_core',
      v1_base_url: 'http://scdsc.uss1.localutm/flight_planning/v1',
    },

    // (optional) Means by which to obtain this participant's software version in the test environment
    test_env_version_provider: {
      participant_id: 'uss1_core',
      interuss: {
        base_url: 'http://scdsc.uss1.localutm/versioning',
      },
    },

    // (optional) Means by which to obtain this participant's software version in the prod environment
    prod_env_version_provider: {
      participant_id: 'uss1_core',
      interuss: {
        base_url: 'http://scdsc.uss1.localutm/versioning',
      },
    },

    // (optional) List of DSS instances hosted by this participant
    dss_instances: [
      {
        participant_id: 'uss1_dss',
        user_participant_ids: [
          // Participants using a DSS instance they do not provide should be listed as users of that DSS (so that they can take credit for USS requirements enforced by the DSS)
          'mock_uss',  // mock_uss uses this DSS instance; it does not provide its own instance
        ],
        base_url: 'http://dss.uss1.localutm',
        supports_ovn_request: true
      },
    ]
  }
}
