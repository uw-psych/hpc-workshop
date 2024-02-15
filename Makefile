SHELL := /bin/bash
.SHELLFLAGS := -e -O xpg_echo -o errtrace -o functrace -c
MAKEFLAGS += --no-builtin-rules
MAKEFLAGS += --no-builtin-variables
MAKE := $(make)
DATETIME_FORMAT := %(%Y-%m-%d %H:%M:%S)T
.ONESHELL:
.SUFFIXES:
.DELETE_ON_ERROR:

# Targets for printing help:
.PHONY: help
help:  ## Prints this usage.
	@printf '== Recipes ==\n' && grep --no-filename -E '^[a-zA-Z0-9-]+:' $(MAKEFILE_LIST) && echo '\n== Images ==' && echo $(SUBDIRS) | tr ' ' '\n' 
# see https://www.gnu.org/software/make/manual/html_node/Origin-Function.html
MAKEFILE_ORIGINS := \
	default \
	environment \
	environment\ override \
	file \
	command\ line \
	override \
	automatic \
	\%

PRINTVARS_MAKEFILE_ORIGINS_TARGETS += \
	$(patsubst %,printvars/%,$(MAKEFILE_ORIGINS)) \

.PHONY: $(PRINTVARS_MAKEFILE_ORIGINS_TARGETS)
$(PRINTVARS_MAKEFILE_ORIGINS_TARGETS):
	@$(foreach V, $(sort $(.VARIABLES)), \
		$(if $(filter $(@:printvars/%=%), $(origin $V)), \
			$(info $V=$($V) ($(value $V)))))

.PHONY: printvars
printvars: printvars/file ## Print all Makefile variables (file origin).

.PHONY: printvar-%
printvar-%: ## Print one Makefile variable.
	@echo '($*)'
	@echo '  origin = $(origin $*)'
	@echo '  flavor = $(flavor $*)'
	@echo '   value = $(value  $*)'

# Make templated files:
JINJA_INPUTS:= $(wildcard */.*.jinja)
JINJA_OUTPUTS := $(join $(dir $(JINJA_INPUTS)), $(patsubst .%,%,$(patsubst %.jinja,%, $(notdir $(JINJA_INPUTS)))))
JINJA_OUTPUTS_DEPS := $(wildcard */.*.inc)

$(JINJA_OUTPUTS): $(JINJA_INPUTS)
	@echo "Rendering $< to $@"
	@jinja2 $< $(JINJA_VARS) -o $@

.PHONY: templated
templated: venv $(JINJA_OUTPUTS) $(JINJA_OUTPUTS_DEPS)

# Set up virtual environment:
REQUIREMENTS_FILES := $(wildcard requirements*.txt) $(wildcard */requirements*.txt)
.PHONY: requirements
requirements: $(REQUIREMENTS_FILES)
	source .venv/bin/activate
	for f in $^; do
		@echo "Installing requirements from \"$$f\""
		@pip install -r "$$f"
	done

.venv:
	@echo "Setting up virtual environment"
	python3 -m venv .venv

.PHONY: venv
venv: .venv

.PHONY: setup
setup: venv requirements

.PHONY: clean
clean:
	@echo "Cleaning up"
	@rm -fv $(JINJA_OUTPUTS)

.PHONY: clean-all
clean-all: clean
	@echo "Removing virtual environment"
	@rm -rf .venv


.PHONY: all
all: setup templated

.DEFAULT_GOAL := help

