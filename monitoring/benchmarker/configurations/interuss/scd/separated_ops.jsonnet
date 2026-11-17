local separated_ops = import './separated_ops.libsonnet';
local environment = import './local_environment.libsonnet';

local num_uss = 3;
local num_nodes = 3;

separated_ops(num_uss, environment.scd_resources(num_uss, num_nodes))
