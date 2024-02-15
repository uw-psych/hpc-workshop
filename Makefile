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

.venv:
	@echo "Setting up virtual environment"
	python3 -m venv .venv
	source .venv/bin/activate
	pip install --upgrade pip


.dev-requirements.installed: requirements-dev.txt | .venv
	@echo "Installing development requirements"
	@source .venv/bin/activate
	@pip install -r $<
	@touch $@

.PHONY: dev-requirements
dev-requirements: .dev-requirements.installed ## Install development requirements.

.PHONY: venv
venv: dev-requirements | .venv ## Create virtual environment and install dev requirements.

.PHONY: install-requirements
install-requirements: $(wildcard */requirements*.txt)
	source .venv/bin/activate
	@for f in $^; do
		@echo "Installing requirements from \"$$f\""
		@pip install -r "$$f"
	@done

.PHONY: requirements
requirements: install-requirements | venv ## Install all requirements from all requirements files.

.PHONY: setup
setup: venv requirements

# Make templated files:
workshop-01/single-job.py: workshop-01/.single-job.py.jinja workshop-01/.bootstats-header.py.inc | .dev-requirements.installed
	@echo "Rendering $< to $@"
	@jinja2 $< $(JINJA_VARS) -o $@
	@chmod +x $@

workshop-01/array-job.py: workshop-01/.array-job.py.jinja workshop-01/.bootstats-header.py.inc | .dev-requirements.installed
	@echo "Rendering $< to $@"
	@jinja2 $< $(JINJA_VARS) -o $@
	@chmod +x $@

TEMPLATED_FILES := workshop-01/single-job.py workshop-01/array-job.py
.PHONY: templated
templated: $(TEMPLATED_FILES) ## Render all templated files.

.PHONY: clean
clean:
	@echo "Cleaning up"
	@rm -fv $(TEMPLATED_FILES)

.PHONY: clean-all
clean-all: clean
	@echo "Removing virtual environment"
	@rm -rf .venv


.PHONY: all
all: setup templated

.DEFAULT_GOAL := help

