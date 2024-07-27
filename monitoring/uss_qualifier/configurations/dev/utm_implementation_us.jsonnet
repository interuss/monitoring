// This file is a top-level test configuration for utm_implementation_us.

// Regardless of environment (which systems are tested and where they are), this baseline defines the overall behavior
// of the test.
local baseline = import 'utm_implementation_us_baseline.libsonnet';

// This environmental information will be provided to the underlying test baseline to form the full test configuration.
// To test a system in a different environment with the same baseline, simply import and provide a different environment
// configuration.
// Note that the environment does not need to be defined in a separate file (utm_implementation_us_env_local.libsonnet).
// If a particular environment specification was not going to be used to create multiple test configurations from
// multiple test baselines, it could be defined directly in this file instead of a separate file.
local env = import 'utm_implementation_us_env_local.libsonnet';

// The full test configuration is the baseline template/function applied/evaluated with our particular environment.
baseline(env)
