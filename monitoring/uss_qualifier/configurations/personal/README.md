UTM Service Testing Guide
This guide details the available InterUSS uss_qualifier tests and how to configure them to test your UTM service.

1. Available Test Suites
   The uss_qualifier tool contains several test suites, each designed to verify compliance with specific standards or requirements.

ASTM Standards
ASTM F3548-21 (Strategic Conflict Detection / Flight Planning)
Suite: suites.astm.utm.f3548_21
Description: Tests strategic coordination, flight planning, conflict detection, and conformance monitoring.
ASTM F3411-22a (Network Remote ID)
Suite: suites.astm.netrid.f3411_22a
Description: Tests Network Remote ID Service Providers (SP) and Display Providers (DP) for the latest standard.
ASTM F3411-19 (Legacy Network Remote ID)
Suite: suites.astm.netrid.f3411_19
Description: Legacy test suite for the 2019 version of the standard.
U-Space (Eurocae)
U-Space Flight Authorization
Suite: suites.uspace.flight_authorisation
(Note: Verify exact path in suites/uspace if using) 2. How to Test Your UTM Service
To test your service, you need to create a Configuration File that tells uss_qualifier two things:

What to test: Which test suite to run.
What to test against: The URL and authentication details of your service.
Step 1: Create a Configuration Directory
Create a folder for your personal configurations, e.g., monitoring/uss_qualifier/configurations/personal.

Step 2: Create a Test Configuration File
Create a file named my_utm_test.yaml in that folder. Use the template below.

Template: Testing a Flight Planning Service (ASTM F3548-21)
This template configures a test where uss_qualifier acts as other USSs to test your USS.

$content_schema: monitoring/uss_qualifier/configurations/configuration/USSQualifierConfiguration.json
v1:
test_run:
action:
test_suite: # 1. Select the Test Suite
suite_type: suites.astm.utm.f3548_21
resources: # Mapping resources required by the suite to your definitions below
flight_planners: flight_planners
dss: dss
utm_auth: utm_auth # ... (other resources mapping)
resources:
resource_declarations: # 2. Define Authentication
utm_auth:
resource_type: resources.communications.AuthAdapterResource
specification:
environment_variable_containing_auth_spec: AUTH_SPEC # 3. Define Your Service (Flight Planner)
flight_planners:
resource_type: resources.flight_planning.FlightPlannersResource
dependencies:
auth_adapter: utm_auth
specification:
flight_planners: - participant_id: my_service_under_test # UPDATE THIS URL to point to your service
v1_base_url: http://host.docker.internal:3000/flight_planning/v1 # 4. Define the DSS (Decision Support Service) # You normally need a DSS to test against. You can use a local mock or a real one.
dss:
resource_type: resources.astm.f3548.v21.DSSInstanceResource
dependencies:
auth_adapter: utm_auth
specification:
participant_id: dss_provider
base_url: http://dss.localutm
execution:
stop_fast: true
artifacts:
raw_report: {}
report_html: {}
Step 3: Run the Test
You can run the test locally using the provided shell script or Docker.

Using run_locally.sh (Linux/Mac/WSL):

# Navigate to the monitoring directory

cd monitoring

# Set your Auth Spec (credentials)

export AUTH_SPEC="DummyOAuth(http://localhost:8085/token, uss_qualifier)"

# Run the test

# Note: The config path is python-module style (dots instead of slashes)

./monitoring/uss_qualifier/run_locally.sh configurations.personal.my_utm_test
Using Docker manually:

docker run --rm -v $(pwd):/app/monitoring \
 -e AUTH_SPEC="DummyOAuth(http://host.docker.internal:8085/token, uss_qualifier)" \
 interuss/monitoring \
 uv run monitoring/uss_qualifier/main.py --config configurations.personal.my_utm_test 3. Key Concepts
Resources: These represent the systems involved in the test.
FlightPlannersResource: Represents USSs that can plan flights. You define your service here.
DSSInstanceResource: The DSS implementation used for the test.
AuthAdapterResource: Handles obtaining access tokens.
Suites: A collection of scenarios.
Scenarios: Individual test logic (e.g., "Nominal Planning", "Conflict with Higher Priority"). 4. Next Steps
Navigate to monitoring/uss_qualifier/configurations/dev to see complex examples like f3548_self_contained.yaml.
Copy a relevant example to configurations/personal/.
Modify the base_url fields to point to your local or staging service.
Run the test and check the report.html generated in monitoring/uss_qualifier/output.
