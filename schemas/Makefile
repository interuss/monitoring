.PHONY: format
format:
	docker run --rm -v "$(CURDIR):/code" -w /code pyfound/black:22.10.0 black .
	./manage_type_schemas.sh --generate

.PHONY: lint
lint:
	docker run --rm -v "$(CURDIR):/code" -w /code pyfound/black:22.10.0 black --check . || (echo "Linter didn't succeed. You can use the following command to fix python linter issues: make format" && exit 1)
	./manage_type_schemas.sh --check
