USER_GROUP := $(shell id -u):$(shell id -g)

UPSTREAM_OWNER := $(shell scripts/git/upstream_owner.sh)
COMMIT := $(shell scripts/git/commit.sh)

ifeq ($(OS),Windows_NT)
  detected_OS := Windows
else
  detected_OS := $(shell uname -s)
endif

.PHONY: format
format:
	cd monitoring && make format

.PHONY: lint
lint: python-lint shell-lint

.PHONY: check-hygiene
check-hygiene: python-lint hygiene validate-uss-qualifier-docs shell-lint

.PHONY: python-lint
python-lint:
	cd monitoring && make python-lint

.PHONY: hygiene
hygiene:
	test/repo_hygiene/repo_hygiene.sh

.PHONY: validate-uss-qualifier-docs
validate-uss-qualifier-docs:
	cd monitoring/uss_qualifier && make validate-docs

.PHONY: shell-lint
shell-lint:
	echo "===== Checking DSS shell lint except monitoring =====" && find . -name '*.sh' | grep -v '^./interfaces/astm-utm' | grep -v '^./monitoring' | xargs docker run --rm -v "$(CURDIR):/monitoring" -w /monitoring koalaman/shellcheck
	cd monitoring && make shell-lint

# This mirrors the hygiene-tests continuous integration workflow job (.github/workflows/ci.yml)
.PHONY: hygiene-tests
hygiene-tests: check-hygiene

.PHONY: build-monitoring
build-monitoring:
	cd monitoring && make build

tag:
	scripts/tag.sh $(UPSTREAM_OWNER)/monitoring/v$(VERSION)

.PHONY: start-locally
start-locally:
	build/dev/run_locally.sh up -d
	build/dev/wait_for_local_dss.sh

.PHONY: probe-locally
probe-locally:
	monitoring/prober/run_locally.sh

.PHONY: start-uss-mocks
start-uss-mocks:
	monitoring/atproxy/run_locally.sh -d
	monitoring/mock_uss/start_all_local_mocks.sh

.PHONY: stop-uss-mocks
stop-uss-mocks:
	monitoring/mock_uss/stop_all_local_mocks.sh
	docker container rm -f atproxy

# The prepended dash ignores errors. This allows collecting logs even if some containers are missing.
.PHONY: collect-local-logs
collect-local-logs:
	mkdir -p logs
	-sh -c "build/dev/run_locally.sh logs --timestamps" > logs/dss_sandbox_local.log 2>&1
	-docker logs atproxy > logs/atproxy.log 2>&1
	-docker logs mock_uss_scdsc > logs/mock_uss_scdsc.log 2>&1
	-docker logs mock_uss_ridsp_v22a > logs/mock_uss_ridsp_v22a.log 2>&1
	-docker logs mock_uss_riddp_v22a > logs/mock_uss_riddp_v22a.log 2>&1
	-docker logs mock_uss_geoawareness > logs/mock_uss_geoawareness.log 2>&1
	-docker logs mock_uss_tracer_v22a > logs/mock_uss_tracer_v22a.log 2>&1
	-docker logs mock_uss_atproxy_client > logs/mock_uss_atproxy_client.log 2>&1

.PHONY: stop-locally
stop-locally:
	build/dev/run_locally.sh stop

.PHONY: down-locally
down-locally:
	build/dev/run_locally.sh down

.PHONY: check-monitoring
check-monitoring:
	cd monitoring && make test

# This mirrors the monitoring-tests continuous integration workflow job (.github/workflows/ci.yml)
.PHONY: monitoring-tests
monitoring-tests: check-monitoring

# This reproduces the entire continuous integration workflow (.github/workflows/ci.yml)
.PHONY: presubmit
presubmit: hygiene-tests monitoring-tests
