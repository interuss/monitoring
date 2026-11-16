/* Simple configuration that creates and deletes ISAs in an automatically-deployed local DSS pool
 * without any contention-causing subscriptions, sweeping through inter-node latency values.
 */

local isas_uncontended = import './isas_uncontended.libsonnet';

local num_uss = 3;
local num_nodes = 3;
local latencies_ms = [50, 25, 1];
local jitter_frac = 0.05;

local nodeIndex = function(uss, node) std.format('%02d', node + num_nodes * (uss - 1));

isas_uncontended(
  num_uss,
  {
    resource_declarations: {
      utm_auth: {
        resource_type: 'resources.communications.AuthAdapterResource',
        specification: {
          auth_spec: 'DummyOAuth(http://localhost:8085/token,benchmarker)',
          scopes_authorized: [
            'rid.service_provider',
            'rid.display_provider',
          ],
        },
      },
    } + {
      ["dss_pool_%d" % uss]: {
        resource_type: 'resources.astm.f3411.DSSInstancesResource',
        dependencies: {
          auth_adapter: 'utm_auth',
        },
        specification: {
          dss_instances: [
            {
              participant_id: 'uss%(uss)d_dss%(node)d' % { uss: uss, node: node },
              base_url: 'http://localhost:80%s/rid/v2' % nodeIndex(uss, node),
              rid_version: 'F3411-22a',
            } for node in std.range(1, num_nodes)
          ],
        },
      } for uss in std.range(1, num_uss)
    },
  },
  [
    {
      name: '%dms internode latency' % latency_ms,
      setup: ['Bring up DSS pool: %dms latency' % latency_ms],
      teardown: ['Tear down DSS pool'],
    } for latency_ms in latencies_ms
  ],
  [
    {
      name: 'Bring up DSS pool: %(latency)dms latency' % { latency: latency_ms },
      run_command: {
        env: {
          NUM_USS: std.toString(num_uss),
          NUM_NODES: std.toString(num_nodes),
          DSS_IMAGE: 'interuss/dss:v0.23.0',
          DB_TYPE: 'crdb',
          INTRA_USS_NETEM_CONF: 'delay 600us 40us 25% distribution normal loss 0.0005%',
          INTER_USS_NETEM_CONF: 'delay %(latency)sms %(jitter)sms 50%% distribution paretonormal loss 0.25%% 15%%' % { latency: latency_ms, jitter: latency_ms * jitter_frac },
        },
        path: '$REPO_ROOT',
        command: 'make start-locally',
      },
    }
    for latency_ms in latencies_ms
  ] + [
    {
      name: 'Tear down DSS pool',
      run_command: {
        env: {
          NUM_USS: std.toString(num_uss),
          NUM_NODES: std.toString(num_nodes),
          DB_TYPE: 'crdb',
        },
        path: '$REPO_ROOT',
        command: 'make clean-locally',
      },
    }
  ],
)
