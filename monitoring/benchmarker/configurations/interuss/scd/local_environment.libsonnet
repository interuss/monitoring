{
  dummy_oauth_resource_declaration: {
    resource_type: 'resources.communications.AuthAdapterResource',
    specification: {
      auth_spec: 'DummyOAuth(http://localhost:8085/token,benchmarker)',
      scopes_authorized: [
        'utm.strategic_coordination',
      ],
    },
  },

  // DSSInstancesResource for the set of 0-based USS indices specified and 0-based node indices specified
  dss_instances_resource_declaration: function(usss, nodes, auth_adapter='utm_auth') {
    resource_type: 'resources.astm.f3548.v21.DSSInstancesResource',
    dependencies: {
      auth_adapter: auth_adapter,
    },
    specification: {
      local nodeIndex = function(uss, node) std.format('%02d', 1 + node + std.length(nodes) * uss),
      dss_instances: std.flattenArrays([
        [
          {
            participant_id: 'uss%(uss)d_dss%(node)d' % { uss: uss, node: node },
            base_url: 'http://localhost:80%s' % nodeIndex(uss, node),
          } for node in nodes
        ] for uss in usss
      ]),
    },
  },

  // Resources declaring utm_auth and uss<N>_dss_pool (1-based) with num_nodes nodes for each of num_uss USSs
  scd_resources: function(num_uss, num_nodes) {
    resource_declarations: {
      utm_auth: $.dummy_oauth_resource_declaration,
    } + {
      ['uss%d_dss_pool' % uss]: $.dss_instances_resource_declaration(
        [uss - 1], std.range(0, num_nodes - 1), 'utm_auth'
      ) for uss in std.range(1, num_uss)
    },
  },
}
