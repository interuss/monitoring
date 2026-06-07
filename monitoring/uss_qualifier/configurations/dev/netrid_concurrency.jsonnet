// This configuration is designed to stress-test local DSS deployments in ways perhaps similar to
// dss#1509 (DSS timeouts during HeavyTrafficConcurrent), and allow partial exploration of dss#1488
// (question regarding number of DSS instances in a pool).

// Before running this configuration, choose a DSS pool size for local deployment.  Set NUM_USS and
// NUM_NODES as both environment variables and below.  Bring up local DSS pool with
// `make start-locally`.  Verify that all containers are healthy and not restarting (#1480) and
// force-remove any containers that are not, then return `make start-locally`.  Repeat until all
// containers are healthy.
//     export NUM_USS=7
//     export NUM_NODES=3

// Choose INT**_USS_NETEM_CONF latency profiles for both intra-instance and inter-instance.  For
// example:
// Cross-zonal GCP latency:
//     export INTRA_USS_NETEM_CONF="delay 600us 40us 25% distribution normal loss 0.0005%"
// 36ms baseline, 280ms tails:
//     export INTER_USS_NETEM_CONF="delay 36ms 40ms 50% distribution paretonormal loss 0.25% 15%"

// Run this configuration with ./monitoring/uss_qualifier/run_locally.sh configurations.dev.netrid_concurrency

// Summarize results with uss_qualifier/scenarios/astm/netrid/common/dss/summarize_heavy_traffic_concurrent.py

local NUM_USS = 7;
local NUM_NODES = 3;

{
  '$content_schema': 'monitoring/uss_qualifier/configurations/configuration/USSQualifierConfiguration.json',
  v1: {
    test_run: {
      action: {
        action_generator: {
          generator_type: 'action_generators.astm.f3411.ForEachDSS',
          resources: {
            dss_instances: 'dss_instances',
            id_generator: 'id_generator',
            service_area: 'service_area',
          },
          specification: {
            dss_instances_source: 'dss_instances',
            dss_instance_id: 'dss',
            action_to_repeat: {
              test_scenario: {
                scenario_type: 'scenarios.astm.netrid.v22a.dss.HeavyTrafficConcurrent',
                resources: {
                  dss: 'dss',
                  id_generator: 'id_generator',
                  isa: 'service_area',
                },
              },
            },
          },
        },
      },
      non_baseline_inputs: [
        'v1.test_run.resources.resource_declarations.utm_auth',
        'v1.test_run.resources.resource_declarations.dss_instances',
      ],
      resources: {
        resource_declarations: {
          utm_auth: {
            resource_type: 'resources.communications.AuthAdapterResource',
            specification: {
              environment_variable_containing_auth_spec: 'AUTH_SPEC',
              scopes_authorized: [
                'rid.service_provider',
                'rid.display_provider',
              ],
            },
          },
          utm_client_identity: {
            resource_type: 'resources.communications.ClientIdentityResource',
            dependencies: {
              auth_adapter: 'utm_auth',
            },
            specification: {
              whoami_audience: 'localhost',
              whoami_scope: 'rid.display_provider',
            },
          },
          id_generator: {
            resource_type: 'resources.interuss.IDGeneratorResource',
            dependencies: {
              client_identity: 'utm_client_identity',
            },
            specification: {},
          },
          service_area_volume: {
            resource_type: 'resources.VolumeResource',
            specification: {
              template: {
                outline_polygon: {
                  vertices: [
                    { lat: 37.1853, lng: -80.6140 },
                    { lat: 37.2148, lng: -80.6140 },
                    { lat: 37.2148, lng: -80.5440 },
                    { lat: 37.1853, lng: -80.5440 },
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
                start_time: {
                  offset_from: {
                    starting_from: {
                      time_during_test: 'TimeOfEvaluation',
                    },
                    offset: '1s',
                  },
                },
                end_time: {
                  offset_from: {
                    starting_from: {
                      time_during_test: 'TimeOfEvaluation',
                    },
                    offset: '1h0m1s',
                  },
                },
              },
            },
          },
          service_area: {
            resource_type: 'resources.netrid.ServiceAreaResource',
            dependencies: {
              volume: 'service_area_volume',
            },
            specification: {
              base_url: 'https://testdummy.interuss.org/interuss/monitoring/uss_qualifier/configurations/dev/library/resources/kentland_service_area',
            },
          },
          dss_instances: {
            resource_type: 'resources.astm.f3411.DSSInstancesResource',
            dependencies: {
              auth_adapter: 'utm_auth',
            },
            specification: {
              dss_instances: [
                {
                  participant_id: 'uss' + i + '_dss' + j,
                  rid_version: 'F3411-22a',
                  base_url: 'http://dss' + j + '.uss' + i + '.localutm/rid/v2',
                }
                for i in std.range(1, NUM_USS)
                for j in std.range(1, NUM_NODES)
              ],
            },
          },
        },
      },
      execution: {
        stop_fast: false,
      },
    },
    artifacts: {
      raw_report: {},
      sequence_view: {},
      timing_report: {
        percentage_of_time_to_break_down: 95,
      },
    },
  },
}
