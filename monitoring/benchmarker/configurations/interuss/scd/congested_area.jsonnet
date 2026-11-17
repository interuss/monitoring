local congested_area = import './congested_area.libsonnet';
local environment = import './local_environment.libsonnet';

local num_uss = 3;
local num_nodes = 3;

congested_area(num_uss, environment.scd_resources(num_uss, num_nodes))
