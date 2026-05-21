// This file defines which participants are involved in which test configurations for the specified environment.
function(env_code)
  // Create a local map of all participants.
  local all_participants = {
    // Every .libsonnet in this folder should be listed except test_membership.
    uss1: import 'uss1.libsonnet',
    uss2: import 'uss2.libsonnet',
    mock_uss: import 'mock_uss.libsonnet',
  };

  // Collect a flat list of all test names from every participant for the given env_code.
  local all_test_names = std.flattenArrays([
    // Safely access the list of tests, providing an empty list as a default.
    std.get(p[env_code], 'participating_in_tests', [])
    // Iterate over each participant object.
    for p in std.objectValues(all_participants)
    // Ensure the participant has a configuration for the current environment.
    if std.objectHas(p, env_code)
  ]);

  // Create a list of unique test names to serve as the keys for active_participants.
  local unique_test_names = std.uniq(std.sort(all_test_names));

  {
    // Defines which participants are active for each specific test configuration in the environment.
    active_participants: {
      // For each unique test name, build an array of participants involved in that test.
      [test_name]: [
        // Iterate over all participants again for each test.
        p
        for p in std.objectValues(all_participants)
        // Check if the current test_name is in this participant's list of tests.
        // This check is also safe against missing keys.
        if std.member(std.get(p[env_code], 'participating_in_tests', []), test_name)
      ]
      // Iterate over the list of unique tests.
      for test_name in unique_test_names
    },

    // Create a union of all active participants from the list of tests above.
    // Note: This assumes each participant object has a unique `participant_id` field to enable de-duplication.
    local all_active_participants_with_duplicates = std.flattenArrays(std.objectValues(self.active_participants)),
    local unique_active_participants = std.uniq(std.sort(all_active_participants_with_duplicates, keyF=function(p) p.participant_id), keyF=function(p) p.participant_id),

    // This list represents all participants that might be have flights that need to be cleared before beginning a test in
    // this environment.
    participants_in_env_to_clear: unique_active_participants,
  }
