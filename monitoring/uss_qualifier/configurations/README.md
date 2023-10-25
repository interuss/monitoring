# uss_qualifier configurations

## Usage

To execute a test run with uss_qualifier, a uss_qualifier configuration must be provided.  This configuration consists of the test suite to run, along with definitions for all resources needed by that test suite, plus information about artifacts that should be generated.  See [`USSQualifierConfiguration`](configuration.py) for the exact schema and [the dev configurations](./dev) for examples.

### Specifying

When referring to a configuration, three methods may be used; see [`FileReference` documentation](../fileio.py) for more details.

* **Package-based**: refer to a dictionary (*.json, *.yaml) file located in a subfolder of the `uss_qualifier` folder using the Python module style, omitting the extension of the file name.  For instance, `configurations.dev.uspace` would refer to [uss_qualifier/configurations/dev/uspace.yaml](dev/uspace.yaml).
* **Local file**: when a configuration reference is prefixed with `file://`, it refers to a local file using the path syntax of the host operating system.
* **Web file**: when a configuration reference is prefixed with `http://` or `https://`, it refers to a file accessible at the specified URL.

### Building

A valid configuration file must provide a single instance of the [`USSQualifierConfiguration` schema](configuration.py) in the format chosen (JSON or YAML), as indicated by the file extension (.json or .yaml).

#### Personalization

When designing personalized/custom configuration files for specific, non-standard systems, the configuration files should generally be stored in either [uss_qualifier/configurations/personal](personal), or in an external repository and provided via `file://` prefix or `http(s)://` prefix.

#### References

To reduce repetition in similar configurations, the configuration parser supports the inclusion of all or parts of other files by using a `$ref` notation similar to (but not the same as) OpenAPI.

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
