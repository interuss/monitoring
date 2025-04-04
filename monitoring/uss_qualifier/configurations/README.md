# uss_qualifier configurations

## Usage

To execute a test run with uss_qualifier, a uss_qualifier configuration must be provided.  This configuration consists of the test suite to run, along with definitions for all resources needed by that test suite, plus information about artifacts that should be generated.  See [`USSQualifierConfiguration`](configuration.py) for the exact schema and [the dev configurations](./dev) for examples.

### Terminology

![Terminology flow chart](assets/terminology.png)

* **Test configuration**: A configuration following the [`USSQualifierConfiguration`](configuration.py) schema which fully defines the actions uss_qualifier should perform when run.  This is the primary input to uss_qualifier and is fully defined by the combination of the test baseline configuration and the test environment configuration.  See ["Specifying"](#specifying) and ["Building"](#building) for more information.
* **Test baseline configuration**: A configuration defining the behavior of the test, but generally omitting which systems are to be tested and where those systems are located.  A test baseline configuration is defined as everything in a test configuration except those elements of the configuration explicitly identified as [`non_baseline_inputs`](configuration.py).
* **Test environment configuration**: The portions of a test configuration explicitly identified as [`non_baseline_inputs`](configuration.py) and generally corresponding with which systems are to be tested and where those systems are located.
* **Test baseline identifier**: An identifier that corresponds to the test baseline configuration + InterUSS `monitoring` codebase version used to run the configuration.  This identifier has the characteristics of a hash: whenever any element of the test baseline configuration changes, the test baseline identifier should change as well.  Given just the test baseline identifier, there is not enough information to construct the corresponding test baseline configuration.  The long-form test baseline identifier is a long hexadecimal hash and can be found in the [`baseline_signature` field of a TestRunReport](../reports/report.py).  This long-form identifier is shortened to a short-form identifier by combining a `TB-` prefix with the first 7 characters of the long-form identifier in certain human-facing artifacts.
* **Test environment identifier**: An identifier that corresponds to the test environment configuration.  This identifier is identical to the test baseline identifier except that it hashes the test environment configuration rather than the test baseline configuration + InterUSS `monitoring` codebase version, its long-form identifier can be found in the [`environment_signature` field of a TestRunReport](../reports/report.py), and its short-form identifier is prefixed with `TE-`.
* **Test run report**: The full set of information captured for a test run is recorded in a [`TestRunReport` object](../reports/report.py), and often written to report.json.  This information is the test run report, and it is the basis for creating all other test artifacts.
* **Test run identifier**: An identifier that corresponds to a particular test run.  This identifier is identical to the test baseline identifier except that it hashes the test run report rather than the test baseline configuration + InterUSS `monitoring` codebase version, and its short-form identifier is prefixed with `TR-`.

### Specifying

When referring to a configuration, three methods may be used; see [`FileReference` documentation](../fileio.py) for more details.

Regardless of method used to refer to a configuration, the content of that configuration must be dict (JSON-like) content following the [`USSQualifierConfiguration`](configuration.py) schema.

* **Package-based**: refer to a dictionary (*.json, *.yaml, *.jsonnet) file located in a subfolder of the `uss_qualifier` folder using the Python module style, omitting the extension of the file name.  For instance, `configurations.dev.uspace` would refer to [uss_qualifier/configurations/dev/uspace.yaml](dev/uspace.yaml).
* **Local file**: when a configuration reference is prefixed with `file://`, it refers to a local file using the path syntax of the host operating system.
* **Web file**: when a configuration reference is prefixed with `http://` or `https://`, it refers to a file accessible at the specified URL.

#### Accessing private GitHub repos

If some or all of a test configuration is located in a private GitHub repo, uss_qualifier can be configured to retrieve that private configuration content in the same way it retrieves publicly-available configuration content.  To enable this:

* Enable personal access tokens in the organization (if the repo is owned by an organization)
    * Go to Settings from the organization page
    * On the left under "Third-party Access", expand "Personal access tokens" and click on "Settings"
    * Allow access to fine-grained personal access tokens
        * For increased security, recommended settings are to require administrator approval and to restrict access to classic personal access tokens, but these settings are up to the organization administrator's discretion
* Create a personal access token capable of viewing the private repo
    * With the GitHub user who will be executing (or managing the execution of) uss_qualifier, navigate to user "Settings"
    * On the left at the very button, navigate to "Developer settings"
    * On the left, expand "Personal access tokens" and navigate to "Fine-grained tokens"
    * Click "Generate new token"
    * Name the token something descriptive; e.g., "Read-only access to private repos"
    * Under "Resource owner", select the appropriate owner (the organization, if the repo is owned by an organization)
    * Under "Repository access", select "Only select repositories" and select the private repos to be accessed
    * Under "Permissions", expand "Repository permissions" and change "Contents" to "Access: read-only"
    * Create the token and copy the value to a secure location
* Identify the private repos and provide the personal access token to uss_qualifier
    * Before running uss_qualifier, populate the environment variable `GITHUB_PRIVATE_REPOS`
        * The value of this environment variable should be a series of private repositories declarations delimited with semicolons
        * Each private repositories declaration should follow the format `ORG_NAME/REPO_NAMES:PAT` where
            * `ORG_NAME` is the name of the GitHub organization or user who owns the repository
            * `REPO_NAMES` is a comma-separated listed of private repos
            * `PAT` is the personal access token
        * Example: `interuss/secret_repo1,secret_repo2:github_pat_abcdefg01234_foobar;interuss_collaborator/other_secret_repo:github_pat_zyxw987_baz`

Now, references to content in these private repos can be used in configurations.  For instance:

```yaml
$ref: https://raw.githubusercontent.com/interuss/secret_repo1/main/configuration/test_baseline.yaml
```

```jsonnet
local test_environment = import 'https://raw.githubusercontent.com/interuss_collaborator/other_secret_repo/1234abcdef/configuration/test_environment.libsonnet';
```

### Building

A valid test configuration file must provide a single instance of the [`USSQualifierConfiguration` schema](configuration.py) in the format chosen (JSON, YAML, Jsonnet), as indicated by the file extension (.json, .yaml, or .jsonnet).

Note that the configuration file may use or refer to other files via [$refs](#references) in JSON, YAML, or Jsonnet.  Jsonnet files may also use or refer to other files via [imports](https://jsonnet.org/learning/tutorial.html#imports).  See the continuous integration test configurations in the [dev folder](dev) for examples.

#### Contents

The contents of a test configuration are a JSON-like representation of an instance of the [`USSQualifierConfiguration` schema](configuration.py).  The JSON schema validating this type can be found in the [USSQualifierConfiguration.json](../../../schemas/monitoring/uss_qualifier/configurations/configuration/USSQualifierConfiguration.json) JSON schema file.  A USSQualifierConfiguration includes specification of:

1. Information necessary to define the test activities to be performed
    1. Test action to execute ([test suite](../README.md#architecture), [test scenario](../README.md#architecture), etc)
    2. Specification of all [resources](../resources/README.md) that will be used in all test scenarios executed to fulfill the specified test action, including:
        1. Information about test participants' systems (e.g., base URLs of APIs needed for testing)
        2. Information about test environment infrastructure (e.g., auth server location, how to obtain access tokens, etc)
        3. Test data (e.g., location and characteristics of flights to request, geographic areas to query, etc)
    3. Which portions (if any) of the test configuration should be considered part of the ["test environment configuration"](#terminology) and not the ["test baseline configuration"](#terminology).  Unless specified here, every part of the test configuration is considered part of the "test baseline configuration".  The test baseline identifier is computed from the contents of the test configuration excluding the portions of the test configuration identified as non-baseline here.
2. [Artifacts](../reports/README.md) (if any) to produce from the test run
3. Validation criteria, if uss_qualifier should exit with an error code based on the outome of the test activities

An optional convention encouraged in test configurations is to annotate the type of objects whose type may be unclear (especially resource declarations) with a `$content_schema` key containing, as its value, the path to the JSON schema of the object type relative to the [`schemas`](../../../schemas) folder.  These annotations are not required and are not used at runtime by uss_qualifier, but [can be used](../../../schemas/README.md) to improve the ease of editing test configuration files.  Note these annotations take advantage of the behavior that all keys present in a test configuration, but not specified in the appropriate schema, are ignored by uss_qualifier.

#### Personalization

When designing personalized/custom configuration files for specific, non-standard systems, the configuration files should generally be stored in either [uss_qualifier/configurations/personal](personal), or in an external repository and provided via `file://` prefix or `http(s)://` prefix.

#### References

To reduce repetition in similar configurations, the configuration parser supports the inclusion of all or parts of other files by using a `$ref` notation similar to (but not the same as) OpenAPI in JSON, YAML, and Jsonnet files.

When a `$ref` key is encountered, the keys and values of the referenced content are used to overwrite any keys at the same level of the `$ref`.  For instance:

_x.json_:
```json
{"a": 1, "$ref": "y.json", "b": 2}
```

_y.json_:
```json
{"b": 3, "c": 4}
```

Loading _x.json_ results in the object:

```json
{"a": 1, "b": 3, "c": 4}
```

To combine the contents from multiple `$ref` sources, use `allOf`.  For instance:

_q.json_:
```json
{"a": 1, "b": 2, "allOf": [{"$ref": "r.json"}, {"$ref": "s.json"}], "c": 3, "d":  4}
```

_r.json_:
```json
{"b": 5, "c": 6, "e":  7}
```

_s.json_:
```json
{"b": 8, "d": 9, "f": 10}
```

Loading _q.json_ results in the object:

```json
{"a": 1, "b": 8, "c": 6, "d": 9, "e": 7, "f": 10}
```

More details may be found in [`fileio.py`](../fileio.py).

## Execution control

To skip or selectively execute portions of a test run defined by a configuration, populate [the `execution` field of the `TestConfiguration`](configuration.py).  This field controls execution of portions of the test run by skipping actions according to specified criteria.  When debugging, this feature can be used to selectively execute only a scenario (or set of scenarios) of interest, or exclude a problematic scenario (or set of scenarios) from execution.  Some examples are shown below:

### Skip all test scenarios:

_Shows test suite / action generator structure_

```yaml
execution:
  skip_action_when:
    - is_test_scenario: {}
```

### Skip a particular test suite

```yaml
execution:
  skip_action_when:
    - is_test_suite:
        types: [suites.astm.netrid.f3411_22a]
```

### Only run two kinds of scenarios

```yaml
execution:
  include_action_when:
    - is_action_generator: {}
    - is_test_suite: {}
    - is_test_scenario:
        types: [scenarios.interuss.mock_uss.configure_locality.ConfigureLocality, scenarios.astm.utm.FlightIntentValidation]
```

### Only run the first, ninth, and tenth test scenarios in the test run

```yaml
execution:
  include_action_when:
    - is_action_generator: {}
    - is_test_suite: {}
    - nth_instance:
        n: [{i: 1}, {lo: 9, hi: 10}]
        where_action:
            is_test_scenario: {}
```

### Only run test scenarios with a matching name

```yaml
execution:
  include_action_when:
    - is_action_generator: {}
    - is_test_suite: {}
    - is_test_scenario: {}
      regex_matches_name: 'ASTM NetRID DSS: Simple ISA'
```

### Run everything except two kinds of test suites

```yaml
execution:
  include_action_when:
    - is_action_generator: {}
    - is_test_suite: {}
      except_when:
        - regex_matches_name: 'ASTM F3411-22a'
        - is_test_suite:
            types: [suites.astm.utm.f3548_21]
    - is_test_scenario: {}
```

### Only run the immediate test scenario children of a particular test suite

```yaml
execution:
  include_action_when:
    - is_action_generator: {}
    - is_test_suite: {}
    - is_test_scenario:
      has_ancestor:
        of_generation: 1
        which:
          - is_test_suite: {}
            regex_matches_name: 'DSS testing for ASTM NetRID F3548-21'
```

### Only run test scenarios that are descendants of a particular test suite

```yaml
execution:
  include_action_when:
    - is_action_generator: {}
    - is_test_suite: {}
    - is_test_scenario:
      has_ancestor:
        which:
          - is_test_suite:
              types: [suites.astm.utm.f3548_21]
```

### Only run the third instance of a particular test scenario name

```yaml
execution:
  include_action_when:
    - is_action_generator: {}
    - is_test_suite: {}
    - nth_instance:
        n: [{i: 3}]
        where_action:
          regex_matches_name: 'Nominal planning: conflict with higher priority'
```

### Only run the test scenarios for the second instance of a particular named action generator

```yaml
execution:
  include_action_when:
    - is_action_generator: {}
    - is_test_suite: {}
    - is_test_scenario: {}
      has_ancestor:
        which:
          - nth_instance:
              n: [{i: 2}]
              where_action:
                is_action_generator: {}
                regex_matches_name: 'For each appropriate combination of flight planner\(s\)'
```

## Design notes

1. Even though all the scenarios, cases, steps and checks are fully defined for a particular test suite, the scenarios require data customized for a particular ecosystem – this data is provided as "test resources" which are created from the specifications in a "test configuration".
2. A test configuration is associated with exactly one test action (test scenario, test suite, action generator), and contains descriptions for how to create each of the set of required test resources.
    * The resources required for a particular test definition depend on which test scenarios are included in the test suite.
3. One resource can be used by many different test scenarios.
4. One test scenario may use multiple resources.
5. One class of resources is resources that describe the systems under test and how to interact with them; e.g., "Display Providers under test".
    * This means that most complete test configurations can't be tracked in the InterUSS repository because it wouldn't make sense to list, e.g., Display Provider observation endpoint URLs in the SUSI qual-partners environment.
    * Partial test configurations, including RID telemetry to inject, operational intents to inject, etc, can be tracked in the InterUSS repository, but they could not be used without specifying the missing resources describing systems under test.
