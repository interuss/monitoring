local typical_load = import './typical_load.libsonnet';
local environment = import './local_environment.libsonnet';

local num_uss = 3;
local num_nodes = 3;

typical_load(num_uss, environment.scd_resources(num_uss, num_nodes))
