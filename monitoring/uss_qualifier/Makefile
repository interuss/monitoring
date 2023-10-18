.PHONY: lint
lint: validate-docs python-lint

.PHONY: validate-docs
validate-docs:
	./scripts/validate_test_definitions.sh
	./scripts/format_test_suite_docs.sh --lint

.PHONY: python-lint
python-lint:
	docker run --rm -v "$(CURDIR):/code" -w /code pyfound/black:22.10.0 black --check . || (echo "Linter didn't succeed. You can use the following command to fix python linter issues: make format" && exit 1)

.PHONY: format
format: format-documentation
	docker run --rm -v "$(CURDIR):/code" -w /code pyfound/black:22.10.0 black .

.PHONY: format-documentation
format-documentation:
	./scripts/format_test_documentation.sh
	./scripts/format_test_suite_docs.sh

.PHONY: unit_test
unit_test:
	./scripts/run_unit_tests.sh

.PHONY: test
test: lint unit_test
	./scripts/test_docker_fully_mocked.sh
