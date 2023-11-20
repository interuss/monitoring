.PHONY: lint
lint: validate-docs

.PHONY: validate-docs
validate-docs: check-no-cross-reference
	./scripts/validate_test_definitions.sh
	./scripts/format_test_suite_docs.sh --lint

.PHONY: check-no-cross-reference
check-no-cross-reference:
	./scripts/check-netrid-cross-references.sh

.PHONY: format
format: format-documentation

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
