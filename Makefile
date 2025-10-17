USER_GROUP := $(shell id -u):$(shell id -g)

UPSTREAM_OWNER := $(shell scripts/git/upstream_owner.sh)
COMMIT := $(shell scripts/git/commit.sh)

ifeq ($(OS),Windows_NT)
  detected_OS := Windows
else
  detected_OS := $(shell uname -s)
endif

.PHONY: format
format: image
	docker run --rm -u ${USER_GROUP} -v "$(CURDIR):/app" -w /app interuss/monitoring uv run ruff format
	docker run --rm -u ${USER_GROUP} -v "$(CURDIR):/app" -w /app interuss/monitoring uv run ruff check --fix
	docker run --rm -u ${USER_GROUP} -v "$(CURDIR):/app" -w /app interuss/monitoring uv run basedpyright
	cd monitoring && make format
	cd schemas && make format

.PHONY: lint
lint: shell-lint python-lint
	cd monitoring && make lint
	cd schemas && make lint

.PHONY: check-hygiene
check-hygiene: image lint validate-uss-qualifier-docs
	test/repo_hygiene/repo_hygiene.sh

.PHONY: python-lint
python-lint: image

	docker run --rm -u ${USER_GROUP} -v "$(CURDIR):/app" -w /app interuss/monitoring uv run ruff format --check || (echo "Linter didn't succeed. You can use the following command to fix python linter issues: make format" && exit 1)
	docker run --rm -u ${USER_GROUP} -v "$(CURDIR):/app" -w /app interuss/monitoring uv run ruff check || (echo "Linter didn't succeed. You can use the following command to fix python linter issues: make format" && exit 1)
	shasum -b -a 256 .basedpyright/baseline.json > /tmp/baseline-before.hash
	docker run --rm -u ${USER_GROUP} -v "$(CURDIR):/app" -w /app interuss/monitoring uv run basedpyright || (echo "Typing check didn't succeed. Please fix issue and run make format to validate changes." && exit 1)
	shasum -b -a 256 .basedpyright/baseline.json > /tmp/baseline-after.hash
	diff /tmp/baseline-before.hash /tmp/baseline-after.hash || (echo "Basedpyright baseline changed, probably dues to issues that have been cleanup. Use the following command to update baseline: make format" && exit 1)

.PHONY: validate-uss-qualifier-docs
validate-uss-qualifier-docs:
	cd monitoring/uss_qualifier && make validate-docs

.PHONY: shell-lint
shell-lint:
	find . -name '*.sh' ! -path "./interfaces/*" | xargs docker run --rm -v "$(CURDIR):/monitoring" -w /monitoring koalaman/shellcheck:v0.11.0

.PHONY: unit-test
unit-test:
	cd monitoring && make unit-test

.PHONY: image
image:
	cd monitoring && make image

tag:
	scripts/tag.sh $(UPSTREAM_OWNER)/monitoring/v$(VERSION)

.PHONY: start-locally
start-locally:
	build/dev/run_locally.sh up -d

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

# This reproduces the entire continuous integration workflow (.github/workflows/ci.yml)
.PHONY: presubmit
presubmit: check-hygiene check-monitoring

# For local development when restarts are frequently required (such as when testing changes on the DSS)
.PHONY: restart-all
restart-all: stop-uss-mocks down-locally start-locally start-uss-mocks

# For local development when restarts of the mock USS are frequently required
.PHONY: restart-uss-mocks
restart-uss-mocks: stop-uss-mocks start-uss-mocks
