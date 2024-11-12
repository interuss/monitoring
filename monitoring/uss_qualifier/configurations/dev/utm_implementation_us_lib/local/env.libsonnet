function(participants) {
  // This file contains environmental (non-baseline) parameters for the utm_implementation_us.jsonnet test configuration for the standard local CI environment.
  // It is parameterized on which participants to include in the test.  Each participant is expected to have a "local_env" block in their definitions.
  // Top-level keys are used in utm_implementation_us_baseline.jsonnet when this content is provided as `env`.
  resource_declarations: {
    // Means by which uss_qualifier can obtain authorization to make requests in an ASTM USS ecosystem
    utm_auth: {
      resource_type: 'resources.communications.AuthAdapterResource',
      specification: {
        // To avoid putting secrets in configuration files, the auth spec (including sensitive information) will be read from the AUTH_SPEC environment variable
        environment_variable_containing_auth_spec: 'AUTH_SPEC',
        scopes_authorized: [
          // InterUSS flight_planning v1 automated testing API
          'interuss.flight_planning.direct_automated_test',
          'interuss.flight_planning.plan',
          // InterUSS versioning automated testing API
          'interuss.versioning.read_system_versions',
          // ASTM F3548-21 USS emulation roles
          'utm.strategic_coordination',
        ],
      },
    },

    // A second auth adapter, for DSS tests that require a second set of credentials for accessing the ecosystem.
    // Note that the 'sub' claim of the tokens obtained through this adepter MUST be different from the first auth adapter.
    second_utm_auth: {
      resource_type: 'resources.communications.AuthAdapterResource',
      specification: {
        environment_variable_containing_auth_spec: 'AUTH_SPEC_2',
        scopes_authorized: [
          'utm.strategic_coordination',
        ],
      },
    },

    // Means by which to obtain the versions of participants' systems under test (in the test environment).
    test_env_version_providers: {
      resource_type: 'resources.versioning.VersionProvidersResource',
      dependencies: {
        auth_adapter: 'utm_auth',
      },
      specification: {
        instances: [
          participant.local_env.test_env_version_provider
          for participant in participants
          if 'test_env_version_provider' in participant.local_env
        ],
      },
    },

    // Means by which to obtain the versions of participants' production systems (in a real test, these would be different URLs than test_env_version_providers above).
    prod_env_version_providers: {
      resource_type: 'resources.versioning.VersionProvidersResource',
      dependencies: {
        auth_adapter: 'utm_auth',
      },
      specification: {
        instances: [
          participant.local_env.prod_env_version_provider
          for participant in participants
          if 'prod_env_version_provider' in participant.local_env
        ],
      },
    },

    // Set of USSs capable of being tested as flight planners
    flight_planners: {
      resource_type: 'resources.flight_planning.FlightPlannersResource',
      dependencies: {
        auth_adapter: 'utm_auth',
      },
      specification: {
        flight_planners: [
          participant.local_env.flight_planner
          for participant in participants
          if 'flight_planner' in participant.local_env
        ],
      },
    },

    // Location of DSS instance that can be used to verify flight planning outcomes
    dss: {
      resource_type: 'resources.astm.f3548.v21.DSSInstanceResource',
      dependencies: {
        auth_adapter: 'utm_auth',
      },
      specification: {
        // A USS that hosts a DSS instance is also a participant in the test, even if they don't fulfill any other roles
        participant_id: 'uss1_dss',
        base_url: 'http://dss.uss1.localutm',
        supports_ovn_request: true,
      },
    },

    dss_instances: {
      resource_type: 'resources.astm.f3548.v21.DSSInstancesResource',
      dependencies: {
        auth_adapter: 'utm_auth',
      },
      specification: {
        dss_instances: [
          instance
          for participant in participants
          if 'dss_instances' in participant.local_env
          for instance in participant.local_env.dss_instances
        ],
      },
    },

    // Mock USS that can be used in tests for flight planning, modifying data sharing behavior and recording interactions
    mock_uss: {
      resource_type: 'resources.interuss.mock_uss.client.MockUSSResource',
      dependencies: {
        auth_adapter: 'utm_auth',
      },
      specification: {
        participant_id: 'mock_uss',
        mock_uss_base_url: 'http://scdsc.log.uss6.localutm',
      },
    },
  },

  aggregate_participants: {
    [participant.participant_id]: participant.aggregate_participant_ids
    for participant in participants
    if 'aggregate_participant_ids' in participant
  },

  participant_requirements: {
    [participant.participant_id]: participant.participant_requirements
    for participant in participants
  },
}
