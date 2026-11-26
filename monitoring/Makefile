.PHONY: lint
lint:
	cd uss_qualifier && make lint

.PHONY: format
format:
	cd uss_qualifier && make format

.PHONY: unit-test
unit-test: image-dev
	docker run --rm -u $$(id -u):$$(id -g) -v "$(CURDIR)/..:/app" -w /app interuss/monitoring-dev uv run pytest monitoring/dummy_oauth
	cd uss_qualifier && make unit_test
	cd monitorlib && make unit_test
	cd benchmarker && make unit_test

image: ../uv.lock ../pyproject.toml $(shell find . -type f ! -path "*/output/*" ! -path "*/.*" ! -path "*/__pycache__/*" ! -name image ! -name image-dev ! -name "*.pyc") $(shell find ../interfaces ../build/test-certs -type f)
	./build.sh

image-dev: ../uv.lock ../pyproject.toml $(shell find . -type f ! -path "*/output/*" ! -path "*/.*" ! -path "*/__pycache__/*" ! -name image ! -name image-dev ! -name "*.pyc") $(shell find ../interfaces ../build/test-certs -type f)
	./build.sh dev

.PHONY: test
test:
	cd mock_uss && make test
	cd uss_qualifier && make test
	cd prober && make test
