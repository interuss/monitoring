local env_local = import 'env.libsonnet';
local uss1 = import '../uss1.libsonnet';
local uss2 = import '../uss2.libsonnet';

env_local([uss1, uss2])
