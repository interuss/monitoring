.PHONY: lint
lint:
	cd uss_qualifier && make lint

.PHONY: format
format:
	cd uss_qualifier && make format

.PHONY: unit-test
unit-test:
	cd uss_qualifier && make unit_test

image: ../uv.lock ../pyproject.toml $(shell find . -type f ! -path "*/output/*" ! -name image ! -name *.pyc) $(shell find ../interfaces -type f)
	./build.sh

.PHONY: test
test:
	cd mock_uss && make test
	cd uss_qualifier && make test
	cd prober && make test
