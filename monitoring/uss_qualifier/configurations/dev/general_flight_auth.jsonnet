local resources = import 'library/resources.yaml';
local environment = import 'library/environment.yaml';
local validation = import './library/validation.yaml';

{
  '$content_schema': 'monitoring/uss_qualifier/configurations/configuration/USSQualifierConfiguration.json',
  v1: {
    test_run: {
      resources: {
        resource_declarations: {
          example_flight_check_table: resources.example_flight_check_table,
          flight_intents: {'$ref': 'library/resources.yaml#/che_general_flight_auth_flights'},

          utm_auth: environment.utm_auth,
          uss1_flight_planner: environment.uss1_flight_planner,
        },
        non_baseline_inputs: [
          'v1.test_run.resources.resource_declarations.utm_auth',
          'v1.test_run.resources.resource_declarations.uss1_flight_planner',
        ],
      },
      action: {
        test_scenario: {
          scenario_type: 'scenarios.interuss.flight_authorization.GeneralFlightAuthorization',
          resources: {
            table: 'example_flight_check_table',
            flight_intents: 'flight_intents',
            planner: 'uss1_flight_planner',
          },
        }
      },
      execution: {
        stop_fast: true
      },
    },
    artifacts: {
      raw_report: {},
      sequence_view: {},
      globally_expanded_report: {},
      tested_requirements: [
        {
          report_name: 'requirements',
          requirement_collections: {
            example: {
              requirement_collections: [
                {
                  requirements: [
                    'REQ_001',
                    'REQ_002',
                    'REQ_003',
                    'REQ_004',
                    'REQ_007',
                  ],
                },
              ],
            },
          },
          participant_requirements: {
            uss1: 'example',
          },
        },
      ]
    },
    validation: validation.normal_test,
  }
}
