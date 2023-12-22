USER_GROUP := $(shell id -u):$(shell id -g)

UPSTREAM_OWNER := $(shell scripts/git/upstream_owner.sh)
COMMIT := $(shell scripts/git/commit.sh)

BLACK_EXCLUDES := "/interfaces|/venv"

ifeq ($(OS),Windows_NT)
  detected_OS := Windows
else
  detected_OS := $(shell uname -s)
endif

.PHONY: format
format: json-schema
	docker run --rm -v "$(CURDIR):/code" -w /code pyfound/black:22.10.0 black --exclude=$(BLACK_EXCLUDES) .
	cd monitoring && make format

.PHONY: lint
lint: shell-lint python-lint
	cd monitoring && make lint
	cd schemas && make lint

.PHONY: check-hygiene
check-hygiene: python-lint hygiene validate-uss-qualifier-docs shell-lint json-schema-lint

.PHONY: python-lint
python-lint:
	docker run --rm -v "$(CURDIR):/code" -w /code pyfound/black:22.10.0 black --check --exclude=$(BLACK_EXCLUDES) . || (echo "Linter didn't succeed. You can use the following command to fix python linter issues: make format" && exit 1)

.PHONY: hygiene
hygiene:
	test/repo_hygiene/repo_hygiene.sh

.PHONY: validate-uss-qualifier-docs
validate-uss-qualifier-docs:
	cd monitoring/uss_qualifier && make validate-docs

.PHONY: shell-lint
shell-lint:
	find . -name '*.sh' ! -path "./interfaces/*" | xargs docker run --rm -v "$(CURDIR):/monitoring" -w /monitoring koalaman/shellcheck

.PHONY: json-schema
json-schema:
	cd schemas && make format

.PHONY: json-schema-lint
json-schema-lint:
	cd schemas && make lint

# This mirrors the hygiene-tests continuous integration workflow job (.github/workflows/ci.yml)
.PHONY: hygiene-tests
hygiene-tests: check-hygiene

.PHONY: image
image:
	cd monitoring && make image

tag:
	scripts/tag.sh $(UPSTREAM_OWNER)/monitoring/v$(VERSION)

.PHONY: start-locally
start-locally:
	build/dev/run_locally.sh up -d
	build/dev/wait_for_local_infra.sh

.PHONY: probe-locally
probe-locally:
	monitoring/prober/run_locally.sh

.PHONY: start-uss-mocks
start-uss-mocks:
	monitoring/mock_uss/start_all_local_mocks.sh

.PHONY: stop-uss-mocks
stop-uss-mocks:
	monitoring/mock_uss/stop_all_local_mocks.sh

# The prepended dash ignores errors. This allows collecting logs even if some containers are missing.
.PHONY: collect-local-logs
collect-local-logs:
	mkdir -p logs
	-sh -c "build/dev/run_locally.sh logs --timestamps" > logs/local_infra.log 2>&1
	-docker logs mock_uss_scdsc_a > logs/mock_uss_scdsc_a.log 2>&1
	-docker logs mock_uss_scdsc_b > logs/mock_uss_scdsc_b.log 2>&1
	-docker logs mock_uss_geoawareness > logs/mock_uss_geoawareness.log 2>&1
	-docker logs mock_uss_ridsp > logs/mock_uss_ridsp.log 2>&1
	-docker logs mock_uss_riddp > logs/mock_uss_riddp.log 2>&1
	-docker logs mock_uss_ridsp_v19 > logs/mock_uss_ridsp_v19.log 2>&1
	-docker logs mock_uss_riddp_v19 > logs/mock_uss_riddp_v19.log 2>&1
	-docker logs mock_uss_tracer > logs/mock_uss_tracer.log 2>&1
	-docker logs mock_uss_scdsc_interaction_log > logs/mock_uss_scdsc_interaction_log.log 2>&1

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
