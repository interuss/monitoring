// This file defines which participants are involved in which test configurations.
{
  // Import external participant definitions.
  uss1:: import '../../participants/uss1.libsonnet',
  uss2:: import '../../participants/uss2.libsonnet',
  mock_uss:: import '../../participants/mock_uss.libsonnet',

  // --- Active Participant Lists per Environment ---
  // Defines which participants are active for each specific configuration.
  active_participants: {
    // List of participants to be tested in the Test1
    test_1: [
      $.uss1,
      $.uss2,
    ],

    // List of participants to be tested in a hypothetical Test2 in the same environment
    test_2: [
      $.uss1,
    ],

    // List of participants involved in other tests in this ecosystem, who therefore may have pre-existing flights that
    // need to be cleared from the test area before test execution to ensure a successful test.
    other_tests: [],
  },

  // --- Derived Variables ---

  // Create a union of all active participants from the list of tests above.
  // Note: This assumes each participant object has a unique `participant_id` field to enable de-duplication.
  local all_active_participants_with_duplicates = std.flattenArrays(std.objectValues(self.active_participants)),
  local unique_active_participants = std.uniq(std.sort(all_active_participants_with_duplicates, keyF=function(p) p.participant_id), keyF=function(p) p.participant_id),

  // This list represents all participants that might be have flights that need to be cleared before beginning a test in
  // this environment.
  participants_in_env_to_clear: unique_active_participants,
}
