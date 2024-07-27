{
  // This file contains environmental (non-baseline) parameters for the utm_implementation_us.jsonnet test configuration for the standard local CI environment.
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
          'utm.availability_arbitration',
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
          {
            participant_id: 'uss1_core',
            interuss: {
              base_url: 'http://scdsc.uss1.localutm/versioning',
            },
          },
          {
            participant_id: 'uss2_core',
            interuss: {
              base_url: 'http://scdsc.uss2.localutm/versioning',
            },
          },
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
          {
            participant_id: 'uss1_core',
            interuss: {
              base_url: 'http://scdsc.uss1.localutm/versioning',
            },
          },
          {
            participant_id: 'uss2_core',
            interuss: {
              base_url: 'http://scdsc.uss2.localutm/versioning',
            },
          },
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
          // uss1 is the mock_uss directly exposing flight planning functionality
          {
            participant_id: 'uss1_core',
            v1_base_url: 'http://scdsc.uss1.localutm/flight_planning/v1',
          },

          // uss2 is another mock_uss directly exposing flight planning functionality
          {
            participant_id: 'uss2_core',
            v1_base_url: 'http://scdsc.uss2.localutm/flight_planning/v1',
          },
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
      },
    },

    dss_instances: {
      resource_type: 'resources.astm.f3548.v21.DSSInstancesResource',
      dependencies: {
        auth_adapter: 'utm_auth',
      },
      specification: {
        dss_instances: [
          {
            participant_id: 'uss1_dss',
            user_participant_ids: [
              // Participants using a DSS instance they do not provide should be listed as users of that DSS (so that they can take credit for USS requirements enforced by the DSS)
              'mock_uss',  // mock_uss uses this DSS instance; it does not provide its own instance
            ],
            base_url: 'http://dss.uss1.localutm',
            has_private_address: true, // This should be removed for production systems
          },
          {
            participant_id: 'uss2_dss',
            base_url: 'http://dss.uss2.localutm',
            has_private_address: true, // This should be removed for production systems
          },
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
    uss1: [
      'uss1_core',
      'uss1_dss',
    ],
    uss2: [
      'uss2_core',
      'uss2_dss',
    ],
  },

  participant_requirements: {
    uss1: 'Basic SCD with DSS provision',
    uss2: 'Basic SCD without DSS provision',
  },
}
