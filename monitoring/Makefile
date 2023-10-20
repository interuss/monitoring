.PHONY: lint
lint:
	cd uss_qualifier && make lint

.PHONY: format
format:
	cd uss_qualifier && make format

.PHONY: build
build:
	./build.sh

.PHONY: test
test:
	cd mock_uss && make test
	cd uss_qualifier && make test
	cd prober && make test
