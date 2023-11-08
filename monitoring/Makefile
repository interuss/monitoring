.PHONY: lint
lint:
	cd uss_qualifier && make lint

.PHONY: format
format:
	cd uss_qualifier && make format

image: ../requirements.txt $(shell find . -type f ! -path "*/output/*" ! -name image ! -name *.pyc) $(shell find ../interfaces -type f)
	# Building image due to changes in the following files: $?
	./build.sh

.PHONY: test
test:
	cd mock_uss && make test
	cd uss_qualifier && make test
	cd prober && make test
