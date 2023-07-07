# [Continuous integration](ci.yml)

Before a pull request can be merged into the main branch, it must pass all automated tests for the repository.  This document describes the tests and how to run them locally.

## Repository hygiene (`make check-hygiene`)

### Python lint (`make python-lint`)

### Automated hygiene verification (`make hygiene`)

### uss_qualifier documentation validation (`make validate-uss-qualifier-docs`)

### Shell lint (`make shell-lint`)

### Go lint (`make go-lint`)

## `monitoring` tests (`make check-monitoring`)

### monitorlib tests (`make test` in monitoring/monitorlib)

### mock_uss tests (`make test` in monitoring/mock_uss)

Steps:

* Bring up geoawareness mock_uss
* Run geoawareness pytest

### uss_qualifier tests (`make test` in monitoring/uss_qualifier)

Steps:

* test_docker_fully_mocked.sh with following configurations:
1. U-Space (configurations.dev.uspace)
2. ASTM NETRID v19 (configurations.dev.netrid_v19

### prober tests (`make test` in monitoring/prober)
