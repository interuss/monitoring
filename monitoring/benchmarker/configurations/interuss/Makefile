USER_GROUP := $(shell id -u):$(shell id -g)

# Find all .jsonnet configuration files in subfolders
JSONNET_CONFIGS := $(patsubst ./%,%,$(shell find . -mindepth 2 -type f -name '*.jsonnet' | sort))
# Generate the corresponding .yaml filenames from the .jsonnet filenames
YAML_CONFIGS := $(patsubst %.jsonnet,%.yaml,$(JSONNET_CONFIGS))

COMMON_DEFINITIONS := $(wildcard *.libsonnet)

VALIDATE_TARGETS := $(addprefix validate-,$(JSONNET_CONFIGS))

.PHONY: validate-configs $(VALIDATE_TARGETS)
validate-configs: $(VALIDATE_TARGETS)

.PHONY: image
image:
	$(MAKE) -C ../../.. image

$(VALIDATE_TARGETS): validate-%: % image
	$(call validate_config,$<)

.PHONY: configurations
configurations: $(YAML_CONFIGS)

validate_config = docker container run --rm \
                 -v $(CURDIR):/app/monitoring/benchmarker/configurations/interuss \
                 -u ${USER_GROUP} \
                 -e PYTHONBUFFERED=1 \
                 -w /app/monitoring/benchmarker \
                 interuss/monitoring \
                 uv run benchmark.py \
                     --config file://configurations/interuss/$(1) \
                     --exit-before-execution

build_yaml = docker container run --rm \
                 -v $(CURDIR):/app/monitoring/benchmarker/configurations/interuss \
                 -u ${USER_GROUP} \
                 -e PYTHONBUFFERED=1 \
                 -w /app/monitoring/benchmarker \
                 interuss/monitoring \
                 uv run benchmark.py \
                     --config file://configurations/interuss/$(1).jsonnet \
                     --config-output /app/monitoring/benchmarker/configurations/interuss/$(1).yaml \
                     --exit-before-execution

.SECONDEXPANSION:
%.yaml: %.jsonnet $(COMMON_DEFINITIONS) $$(shell find $$(@D) -type f -name '*.libsonnet') | image
	$(call build_yaml,$(basename $@))
