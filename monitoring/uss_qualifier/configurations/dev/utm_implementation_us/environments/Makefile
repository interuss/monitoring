USER_GROUP := $(shell id -u):$(shell id -g)

# Find all .jsonnet configuration files
JSONNET_CONFIGS := $(shell find . -type f -name '*.jsonnet')
# Generate the corresponding .yaml filenames from the .jsonnet filenames
YAML_CONFIGS := $(patsubst %.jsonnet,%.yaml,$(JSONNET_CONFIGS))

COMMON_DEFINITIONS := $(wildcard ../definitions/*.libsonnet) $(wildcard ../participants/*.libsonnet)

.PHONY: configurations
configurations: $(YAML_CONFIGS)

build_yaml = docker container run \
                 -v $(CURDIR)/..:/app/monitoring/uss_qualifier/configurations/utmimplementationus \
                 -u ${USER_GROUP} \
                 -e PYTHONBUFFERED=1 \
                 -w /app/monitoring/uss_qualifier  \
                 interuss/monitoring \
                 uv run main.py \
                     --config file://configurations/utmimplementationus/environments/$(1).jsonnet \
                     --config-output /app/monitoring/uss_qualifier/configurations/utmimplementationus/environments/$(1).yaml \
                     --exit-before-execution

.SECONDEXPANSION:
%.yaml: %.jsonnet $(COMMON_DEFINITIONS) $$(shell find $$(@D) -type f -name '*.libsonnet')
	$(call build_yaml,$(basename $@))
