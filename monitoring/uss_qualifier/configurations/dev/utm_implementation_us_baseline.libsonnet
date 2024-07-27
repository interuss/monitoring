function(env) {
  // See the file below (in the `schemas` folder of this repo) for the schema this file's content follows
  '$content_schema': 'monitoring/uss_qualifier/configurations/configuration/USSQualifierConfiguration.json',

  // This configuration uses the v1 configuration schema
  v1: {
    // This block defines how to perform a test run
    test_run: {
      // This block defines which test action uss_qualifier should run, and what resources from the pool should be used
      action: {
        test_suite: {
          // suite_type is a FileReference (defined in uss_qualifier/file_io.py) to a test suite definition (see uss_qualifier/suites/README.md)
          suite_type: 'suites.astm.utm.f3548_21',

          // Mapping of <resource name in test suite> to <resource name in resource pool>
          resources: {
            id_generator: 'id_generator',
            utm_client_identity: 'utm_client_identity',
            test_env_version_providers: 'test_env_version_providers',
            prod_env_version_providers: 'prod_env_version_providers',
            flight_planners: 'flight_planners',
            flight_planners_to_clear: 'flight_planners',
            conflicting_flights: 'conflicting_flights',
            invalid_flight_intents: 'invalid_flight_intents',
            non_conflicting_flights: 'non_conflicting_flights',
            dss: 'dss',
            dss_instances: 'dss_instances',
            mock_uss: 'mock_uss',
            second_utm_auth: 'second_utm_auth',
            planning_area: 'planning_area',
            problematically_big_area: 'problematically_big_area',
            system_identity: 'system_identity',
            // dss_crdb_cluster: dss_crdb_cluster  # TODO: Provide once local DSS uses a multi-node cluster
          },
        },
      },

      // When a test run is executed, a "baseline signature" is computed uniquely identifying the "baseline" of the test,
      // usually excluding exactly what systems are participating in the test (the "environment").  This is a list of
      // elements within this configuration to exclude from the configuration when computing the baseline signature.
      non_baseline_inputs: [
        'v1.test_run.resources.resource_declarations.utm_auth',
        'v1.test_run.resources.resource_declarations.second_utm_auth',
        'v1.test_run.resources.resource_declarations.test_env_version_providers',
        'v1.test_run.resources.resource_declarations.prod_env_version_providers',
        'v1.test_run.resources.resource_declarations.flight_planners',
        'v1.test_run.resources.resource_declarations.dss',
        'v1.test_run.resources.resource_declarations.dss_instances',
        'v1.test_run.resources.resource_declarations.mock_uss',
        'v1.test_run.resources.resource_declarations.dss_crdb_cluster',
        'v1.artifacts.tested_requirements[0].aggregate_participants',
        'v1.artifacts.tested_requirements[0].participant_requirements',
      ],

      // This block defines all the resources available in the resource pool.
      // All resources defined below should be used either
      //   1) directly in the test suite or
      //   2) to create another resource in the pool
      resources: {
        resource_declarations: env.resource_declarations + {

          // Means by which uss_qualifier can discover which subscription ('sub' claim of its tokes) it is described by
          utm_client_identity: {
            resource_type: 'resources.communications.ClientIdentityResource',
            dependencies: {
              auth_adapter: 'utm_auth',
            },
            specification: {
              // Audience and scope to be used to issue a dummy query, should it be required to discover the subscription
              whoami_audience: 'localhost',
              whoami_scope: 'utm.strategic_coordination',
            },
          },

          // Means by which uss_qualifier generates identifiers
          id_generator: {
            resource_type: 'resources.interuss.IDGeneratorResource',
            dependencies: {
              client_identity: 'utm_client_identity',
            },
          },

          // Area that will be used for queries and resource creation that are geo-located
          planning_area: {
            resource_type: 'resources.astm.f3548.v21.PlanningAreaResource',
            specification: {
              base_url: 'https://uss_qualifier.test.utm/dummy_base_url',
              volume: {
                outline_polygon: {
                  vertices: [
                    {
                      lat: 37.1853,
                      lng: -80.614,
                    },
                    {
                      lat: 37.2148,
                      lng: -80.614,
                    },
                    {
                      lat: 37.2148,
                      lng: -80.544,
                    },
                    {
                      lat: 37.1853,
                      lng: -80.544,
                    },
                  ],
                },
                altitude_lower: {
                  value: 0,
                  reference: 'W84',
                  units: 'M',
                },
                altitude_upper: {
                  value: 3048,
                  reference: 'W84',
                  units: 'M',
                },
              },
            },
          },

          // An area designed to be soo big as to be refused by systems queries with it.
          problematically_big_area: {
            resource_type: 'resources.VerticesResource',
            specification: {
              vertices: [
                {
                  lat: 33,
                  lng: -96,
                },
                {
                  lat: 32,
                  lng: -96,
                },
                {
                  lat: 32,
                  lng: -95,
                },
                {
                  lat: 33,
                  lng: -95,
                },
              ],
            },
          },

          // Details of conflicting flights (used in nominal planning scenario)
          conflicting_flights: {
            resource_type: 'resources.flight_planning.FlightIntentsResource',
            specification: {
              file: {
                path: 'file://./test_data/flight_intents/standard/conflicting_flights.yaml',
              },
              transformations: [
                {
                  relative_translation: {
                    // Put these flight intents in an appropriate area in Texas
                    degrees_north: 32.3716,
                    degrees_east: -95.3216,
                    // EGM96 geoid is 27.3 meters below the WGS84 ellipsoid at 32.3716, -95.3216
                    // Ground level starts at roughly 143m above the EGM96 geoid
                    // Therefore, ground level is at roughly 116m above the WGS84 ellipsoid
                    meters_up: 116,
                  },
                },
              ],
            },
          },

          // Details of flights with invalid operational intents (used in flight intent validation scenario)
          invalid_flight_intents: {
            resource_type: 'resources.flight_planning.FlightIntentsResource',
            specification: {
              intent_collection: {
                '$ref': 'test_data.flight_intents.standard.invalid_flight_intents',
              },
              transformations: [
                {
                  relative_translation: {
                    degrees_north: 32.3716,
                    degrees_east: -95.3216,
                    meters_up: 116,
                  },
                },
              ],
            },
          },

          // Details of non-conflicting flights (used in data validation scenario)
          non_conflicting_flights: {
            resource_type: 'resources.flight_planning.FlightIntentsResource',
            specification: {
              intent_collection: {
                '$ref': 'test_data.flight_intents.standard.non_conflicting',
              },
              transformations: [
                {
                  relative_translation: {
                    degrees_north: 32.3716,
                    degrees_east: -95.3216,
                    meters_up: 116,
                  },
                },
              ],
            },
          },

          // Name of the system under test for which the system version should be obtained from participants who provide version information
          system_identity: {
            resource_type: 'resources.versioning.SystemIdentityResource',
            specification: {
              system_identity: 'us.utm_implementation',
            },
          },
        }, // resource_declarations
      }, // resources

      // How to execute a test run using this configuration
      execution: {
        // Since we expect no failed checks and want to stop execution immediately if there are any failed checks, we set
        // this parameter to true.
        stop_fast: true,
      },
    }, // test_run

    // This block defines artifacts related to the test run.  Note that all paths are
    // relative to where uss_qualifier is executed from, and are located inside the
    // Docker container executing uss_qualifier.
    artifacts: {
      // Write out full report content
      raw_report: {},

      tested_requirements: [
        // Write out a human-readable reports of the F3548-21 requirements tested
        {
          report_name: 'scd',
          aggregate_participants: env.aggregate_participants,
          requirement_collections: {
            'Basic SCD with DSS provision': {
              requirements: [
                'astm.f3548.v21.GEN0100',
                'astm.f3548.v21.GEN0105',
                'astm.f3548.v21.GEN0300',
                'astm.f3548.v21.GEN0305',
                'astm.f3548.v21.GEN0310',
                'astm.f3548.v21.OPIN0015',
                'astm.f3548.v21.OPIN0020',
                'astm.f3548.v21.OPIN0025',
                'astm.f3548.v21.OPIN0030',
                'astm.f3548.v21.OPIN0035',
                'astm.f3548.v21.OPIN0040',
                'astm.f3548.v21.USS0005',
                'astm.f3548.v21.SCD0035',
                'astm.f3548.v21.SCD0040',
                'astm.f3548.v21.SCD0045',
                'astm.f3548.v21.SCD0050',
                'astm.f3548.v21.SCD0075',
                'astm.f3548.v21.SCD0080',
                'astm.f3548.v21.SCD0085',
                'astm.f3548.v21.GEN0500',
                'astm.f3548.v21.USS0105',
                'astm.f3548.v21.DSS0005,1',
                'astm.f3548.v21.DSS0005,2',
                'astm.f3548.v21.DSS0005,5',
                'astm.f3548.v21.DSS0015',
                'astm.f3548.v21.DSS0020',
                'astm.f3548.v21.DSS0100,1',
                'astm.f3548.v21.DSS0200',
                'astm.f3548.v21.DSS0205',
                'astm.f3548.v21.DSS0210,1a',
                'astm.f3548.v21.DSS0210,1b',
                'astm.f3548.v21.DSS0210,1c',
                'astm.f3548.v21.DSS0210,1d',
                'astm.f3548.v21.DSS0210,1e',
                'astm.f3548.v21.DSS0210,1f',
                'astm.f3548.v21.DSS0210,1g',
                'astm.f3548.v21.DSS0210,1h',
                'astm.f3548.v21.DSS0210,1i',
                'astm.f3548.v21.DSS0210,2a',
                'astm.f3548.v21.DSS0210,2b',
                'astm.f3548.v21.DSS0210,2c',
                'astm.f3548.v21.DSS0210,2d',
                'astm.f3548.v21.DSS0210,2e',
                'astm.f3548.v21.DSS0210,2f',
                'astm.f3548.v21.DSS0210,A2-7-2,1a',
                'astm.f3548.v21.DSS0210,A2-7-2,1b',
                'astm.f3548.v21.DSS0210,A2-7-2,1c',
                'astm.f3548.v21.DSS0210,A2-7-2,1d',
                'astm.f3548.v21.DSS0210,A2-7-2,2a',
                'astm.f3548.v21.DSS0210,A2-7-2,2b',
                'astm.f3548.v21.DSS0210,A2-7-2,3a',
                'astm.f3548.v21.DSS0210,A2-7-2,3b',
                'astm.f3548.v21.DSS0210,A2-7-2,4a',
                'astm.f3548.v21.DSS0210,A2-7-2,4b',
                'astm.f3548.v21.DSS0210,A2-7-2,4c',
                'astm.f3548.v21.DSS0210,A2-7-2,4d',
                'astm.f3548.v21.DSS0210,A2-7-2,5a',
                'astm.f3548.v21.DSS0210,A2-7-2,5b',
                'astm.f3548.v21.DSS0210,A2-7-2,5c',
                'astm.f3548.v21.DSS0210,A2-7-2,7',
                'astm.f3548.v21.DSS0215',
                'astm.f3548.v21.DSS0300',
                'interuss.automated_testing.flight_planning.ClearArea',
                'interuss.automated_testing.flight_planning.DeleteFlightSuccess',
                'interuss.automated_testing.flight_planning.ExpectedBehavior',
                'interuss.automated_testing.flight_planning.FlightCoveredByOperationalIntent',
                'interuss.automated_testing.flight_planning.ImplementAPI',
                'interuss.automated_testing.flight_planning.Readiness',
                'interuss.f3548.notification_requirements.NoDssEntityNoNotification',
              ],
            },
            'Basic SCD without DSS provision': {
              requirements: [
                'astm.f3548.v21.GEN0100',
                'astm.f3548.v21.GEN0105',
                'astm.f3548.v21.GEN0300',
                'astm.f3548.v21.GEN0305',
                'astm.f3548.v21.GEN0310',
                'astm.f3548.v21.OPIN0015',
                'astm.f3548.v21.OPIN0020',
                'astm.f3548.v21.OPIN0025',
                'astm.f3548.v21.OPIN0030',
                'astm.f3548.v21.OPIN0035',
                'astm.f3548.v21.OPIN0040',
                'astm.f3548.v21.USS0005',
                'astm.f3548.v21.SCD0035',
                'astm.f3548.v21.SCD0040',
                'astm.f3548.v21.SCD0045',
                'astm.f3548.v21.SCD0050',
                'astm.f3548.v21.SCD0075',
                'astm.f3548.v21.SCD0080',
                'astm.f3548.v21.SCD0085',
                'astm.f3548.v21.GEN0500',
                'astm.f3548.v21.USS0105',
                'interuss.automated_testing.flight_planning.ClearArea',
                'interuss.automated_testing.flight_planning.DeleteFlightSuccess',
                'interuss.automated_testing.flight_planning.ExpectedBehavior',
                'interuss.automated_testing.flight_planning.FlightCoveredByOperationalIntent',
                'interuss.automated_testing.flight_planning.ImplementAPI',
                'interuss.automated_testing.flight_planning.Readiness',
                'interuss.f3548.notification_requirements.NoDssEntityNoNotification',
              ],
            },
          },
          participant_requirements: env.participant_requirements,
        },
      ], // tested_requirements

      // Write out a human-readable report showing the sequence of events of the test
      sequence_view: {},
    }, // artifacts

    validation: {
      // This block defines whether to return an error code from the execution of uss_qualifier, based on the content of the
      // test run report.  All the criteria must be met to return a successful code.
      criteria: [
        {
          // applicability indicates which test report elements the pass_condition applies to
          applicability: {
            // We want to make sure no test scenarios had execution errors
            test_scenarios: {},
          },
          pass_condition: {
            each_element: {
              has_execution_error: false,
            },
          },
        },
        {
          applicability: {
            // We also want to make sure there are no failed checks...
            failed_checks: {
              // ...at least, no failed checks with severity higher than "Low".
              has_severity: {
                higher_than: 'Low',
              },
            },
          },
          pass_condition: {
            // When considering all the applicable elements...
            elements: {
              // ...the number of applicable elements should be zero.
              count: {
                equal_to: 0,
              },
            },
          },
        },
      ], // criteria
    }, // validation
  }, // v1
}
