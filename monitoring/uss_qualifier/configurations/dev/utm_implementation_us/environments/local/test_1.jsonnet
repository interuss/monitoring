// This file is a top-level test configuration for "Test 1" of utm_implementation_us.

// Regardless of environment (which systems are tested and where they are), this baseline defines the overall behavior
// of the test.
local baseline = import '../../definitions/baseline_a.libsonnet';

// Environmental information will be provided to the underlying test baseline to form the full test configuration.
// This template provides appropriate environmental information for baseline_a.  Note that this template is a
// parameterized function and should therefore be usable for a range of different environments.
local env_template = import '../../definitions/env_template_a.libsonnet';

// This resource provides membership in the tests defined for this environment.
local test_membership = import '../../participants/test_membership.libsonnet';
local limit_to = import '../../participants/limit_to.libsonnet';

// This resource describes the mock_uss instance to be used in the test.
local mock_uss = import '../../participants/mock_uss.libsonnet';

// The concrete environment depends on which environment is being used and which participants are included; those
// participants are specified here so the concrete environment definition can be rendered.
local env_code = 'local_env';  // Environment code; each participant below must define a block with this name
local allow_list = ['uss1', 'uss2'];  // Participants who may participate in this test if they choose to
local env = env_template(
  env_code,
  'DummyOAuth(http://oauth.authority.localutm:8085/token,uss_qualifier)',  // Means by which to obtain access tokens for the next-higher environment (to retrieve prod versions)
  limit_to(test_membership(env_code).active_participants.test_1, allow_list),  // Allowed active participants
  test_membership(env_code).participants_in_env_to_clear,  // Participants for which pre-existing flights should be cleared
  mock_uss,  // mock_uss participant
);

// The full test configuration is the baseline template/function applied/evaluated with our particular concrete environment.
baseline(env)
