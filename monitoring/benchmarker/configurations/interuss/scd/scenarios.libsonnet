local actions = import './actions.libsonnet';
local artifacts = import '../artifacts.libsonnet';
local environment = import './local_environment.libsonnet';
local loads = import '../loads.libsonnet';

{
  /* Apply a flight planner user-count search to each DSS instance in turn.  user_types_by_uss is an
   * array of arrays of user specifications, one array per USS.  Users are assigned
   * round-robin within each array; repeated entries can weight traffic toward busy sites.
   * subscriptions is an array of {id, rect} objects, established before the first search
   * and removed after the last.
   */
  flight_planner_search: function(test_name, num_nodes, initial_users, user_types_by_uss, subscriptions) {
    local num_uss = std.length(user_types_by_uss),
    local subscription_indices = std.range(0, std.length(subscriptions) - 1),

    resources: {
      resource_declarations: {
        utm_auth: environment.dummy_oauth_resource_declaration,
      } + {
        ['uss%d_dss_pool' % uss]: environment.dss_instances_resource_declaration(
          [uss - 1], std.range(0, num_nodes - 1), 'utm_auth'
        ) for uss in std.range(1, num_uss)
      },
    },

    actions: [
      {
        name: 'Generate intermediate artifacts',
        generate_artifacts: {
          subfolder: 'f"intermediate{action_invocation}"',
          defined_artifact_indices: [0, 1, 2],
        },
      },
    ] + [
      actions.create_subscription(
        'Create subscription %d' % (i + 1), subscriptions[i].id, subscriptions[i].rect
      ) for i in subscription_indices
    ] + [
      actions.delete_subscription(
        'Delete subscription %d' % (i + 1), subscriptions[i].id
      ) for i in subscription_indices
    ],

    user_types: std.flattenArrays(user_types_by_uss),

    loads: [
      local user_types = user_types_by_uss[uss - 1];
      {
        name: 'Flight planner search for USS %d' % uss,
        user_search: {
          user_types: [u.name for u in user_types],
          initial_users: initial_users,
          user_expansion_ratio: 2,
          random_seed: 1234,
          throughput_stability_criteria: loads.normal_flights_stability_criteria,
          throughput_instability_criteria: loads.normal_flights_instability_criteria,
          step_completion_criteria: loads.normal_flights_completion_criteria,
          search_completion_criteria: {
            adjacency_user_count: 2,
            consecutive_unstable_user_counts: 3,
            consecutive_stable_user_counts: 3,
            maximum_left_side_spacing: 0.2,
            max_throughput_adjacent_user_counts: 2,
          },
        },
      } for uss in std.range(1, num_uss)
    ],

    scenarios: [
      {
        name: 'DSS instance %d' % uss,
        [if uss == 1 then 'setup']: ['Create subscription %d' % (i + 1) for i in subscription_indices],
        load: 'Flight planner search for USS %d' % uss,
        teardown:
          (if uss < num_uss then ['Generate intermediate artifacts'] else [])
          + (if uss == num_uss then ['Delete subscription %d' % (i + 1) for i in subscription_indices] else []),
      } for uss in std.range(1, num_uss)
    ],

    artifacts: [
      {
        raw_report: {
          name: 'report',
        },
      },
      artifacts.scd_flights_timeline,
      artifacts.throughput_latency_plots('scalability_curve', test_name, num_uss, num_uss),
      {
        usslogset: {
          include_headers: ['Authorization'],
        },
      },
    ],
  },
}
