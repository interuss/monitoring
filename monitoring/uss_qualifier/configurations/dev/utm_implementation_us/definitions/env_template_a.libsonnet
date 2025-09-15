// This file contains environmental (non-baseline) parameters corresponding to the baseline in baseline_a.libsonnet.
// It is parameterized on environmental aspects; see documentation below.
// Each participant is expected to have a block in their definitions corresponding to the value of `env_code`, and the content of this block will be used.
// Top-level keys of this file's function result are used in baseline_a.libsonnet when this content is provided as `env`.

function(env_code, next_env_auth_spec, active_participants, participants_to_clear, mock_uss)
  // env_code: String specifying which environment block to extract from each participant.
  // next_env_auth_spec: Auth spec that should be used to obtain tokens for the next-higher environment (e.g., production) to obtain system versions in that environment
  // active_participants: Array of object-per-participant with an `env_code`-keyed block containing resources for that participant (see ../participants folder).
  // participants_to_clear: Same as `active_participants`, but only the `flight_planner` resource is used to clear flights for these participants before primary testing begins.
  // mock_uss: A single element in the form of `active_participants` elements describing the mock_uss participant.

  // Utility function to append resources from mock_uss if (and only if) it is not listed
  // as an active participant (since, in that case, its resources will already be present).
  local extract_from_mock_uss_if_not_active = function(field)
    if (field in mock_uss[env_code]
      && std.length(std.find(mock_uss, active_participants)) == 0)
    then [mock_uss[env_code][field]]
    else [];

  {
  resource_declarations: {
    // Means by which uss_qualifier can obtain authorization to make requests in an ASTM USS ecosystem.
    utm_auth: {
      resource_type: 'resources.communications.AuthAdapterResource',
      specification: {
        // To avoid putting secrets in configuration files, the auth spec (including sensitive information) will be read from the AUTH_SPEC environment variable.
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

    // An auth adapter providing access to the next-higher environment for the purpose of determining system versions
    // in that next environment.
    next_env_auth: {
      resource_type: 'resources.communications.AuthAdapterResource',
      specification: {
        auth_spec: next_env_auth_spec,
        scopes_authorized: [
          // InterUSS versioning automated testing API
          'interuss.versioning.read_system_versions',
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
        participant_id: mock_uss.participant_id,
        mock_uss_base_url: mock_uss[env_code].mock_uss_base_url,
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
          participant[env_code].test_env_version_provider
          for participant in active_participants
          if 'test_env_version_provider' in participant[env_code]
        ] + extract_from_mock_uss_if_not_active('test_env_version_provider'),
      },
    },

    // Means by which to obtain the versions of participants' production systems (in a real test, these would be different URLs than test_env_version_providers above).
    prod_env_version_providers: {
      resource_type: 'resources.versioning.VersionProvidersResource',
      dependencies: {
        auth_adapter: 'next_env_auth',
      },
      specification: {
        instances: [
          participant[env_code].prod_env_version_provider
          for participant in active_participants
          if 'prod_env_version_provider' in participant[env_code]
        ],
      },
    },

    // Set of USSs being tested as flight planners
    flight_planners: {
      resource_type: 'resources.flight_planning.FlightPlannersResource',
      dependencies: {
        auth_adapter: 'utm_auth',
      },
      specification: {
        flight_planners: [
          participant[env_code].flight_planner
          for participant in active_participants
          if 'flight_planner' in participant[env_code]
        ],
      },
    },

    // Full set of flight planning USSs in the environment that may have dangling operational intents that need to be cleaned
    flight_planners_to_clear: {
      resource_type: 'resources.flight_planning.FlightPlannersResource',
      dependencies: {
        auth_adapter: 'utm_auth',
      },
      specification: {
        flight_planners: [
          participant[env_code].flight_planner
          for participant in participants_to_clear
          if 'flight_planner' in participant[env_code]
        ] + extract_from_mock_uss_if_not_active('flight_planner'),
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
          for participant in active_participants
          if 'dss_instances' in participant[env_code]
          for instance in participant[env_code].dss_instances
        ],
      },
    },

    // Location of DSS instance that can be used to verify flight planning outcomes
    dss: {
      resource_type: 'resources.astm.f3548.v21.DSSInstanceResource',
      dependencies: {
        auth_adapter: 'utm_auth',
      },
      specification: [
          instance
          for participant in active_participants
          if 'dss_instances' in participant[env_code]
          for instance in participant[env_code].dss_instances
        ][0],
    },

    // Datastore cluster constituting the DSS Airspace Representation
//    dss_datastore_cluster: {
//      resource_type: 'resources.interuss.datastore.DatastoreDBClusterResource',
//      specification: {
//        nodes: [
//          node
//          for participant in active_participants
//          if 'dss_datastore_cluster_nodes' in participant[env_code]
//          for node in participant[env_code].dss_datastore_cluster_nodes
//        ],
//      },
//    },

  },

  aggregate_participants: {
    [participant.participant_id]:
      (if env_code in participant && 'aggregate_participant_ids' in participant[env_code] then
        participant[env_code].aggregate_participant_ids
      else
        participant.aggregate_participant_ids)
      for participant in active_participants
      if 'aggregate_participant_ids' in participant ||
        (env_code in participant && 'aggregate_participant_ids' in participant[env_code])
  },

  participant_requirements: {
    [participant.participant_id]: participant.participant_requirements
    for participant in active_participants
  },
}
