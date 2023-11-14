#!make

.ONESHELL:
SHELL=/bin/bash

################################################
### Snakemake
################################################

### 1. change these settings or override with env variables
CONFIG?=configs/config.prod.yml
CONDA_PATH?=../mambaforge
SNAKEMAKE_OUTPUT_CACHE?=../cache
PROFILE?=local
# execution rule or path to rule output, default is all
TARGET=
REPORTS?=../reports
# for tensorboard
MODELS?=../models
LOGS_TASK_GROUP?=

###

CONDA_ACTIVATE=source $(CONDA_PATH)/etc/profile.d/conda.sh ; conda activate ; conda activate
SNAKEMAKE=export SNAKEMAKE_OUTPUT_CACHE=$(SNAKEMAKE_OUTPUT_CACHE); snakemake

### 2. setup

git-modules:
	git submodule update --init --recursive

conda:
	wget https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$$(uname)-$$(uname -m).sh
	bash Mambaforge-$$(uname)-$$(uname -m).sh -b -p $(CONDA_PATH)

snakemake:
	$(CONDA_ACTIVATE) base
	mamba create -c conda-forge -c bioconda -n snakemake snakemake==6.12.2 tabulate==0.8.10 --yes
	mkdir -p "$(SNAKEMAKE_OUTPUT_CACHE)"

# build container image for cluster and run-local modes (preferred)
build:
	sudo singularity build Singularity.sif Singularity.def

# or pull container image from a registry if there is no sudo
pull:
	singularity pull Singularity.sif library://evgenypavlov/default/bergamot2:latest

### 3. dry run

# if you need to activate conda environment for direct snakemake commands, use
# . $(CONDA_PATH)/etc/profile.d/conda.sh && conda activate snakemake

dry-run:
	echo "Dry run with config $(CONFIG) and profile $(PROFILE)"
	$(CONDA_ACTIVATE) snakemake
	$(SNAKEMAKE) \
	  --profile=profiles/$(PROFILE) \
	  --configfile $(CONFIG) \
	  -n \
	  $(TARGET)

test-dry-run: CONFIG=configs/config.test.yml
test-dry-run: dry-run

### 4. run

run:
	echo "Running with config $(CONFIG) and profile $(PROFILE)"
	$(CONDA_ACTIVATE) snakemake
	chmod +x profiles/$(PROFILE)/*
	$(SNAKEMAKE) \
	  --profile=profiles/$(PROFILE) \
	  --configfile $(CONFIG) \
	  $(TARGET)

test: CONFIG=configs/config.test.yml
test: run


### 5. create a report

report:
	$(CONDA_ACTIVATE) snakemake
    DT=$$(date '+%Y-%m-%d_%H-%M'); \
	mkdir -p $(REPORTS) && \
	snakemake \
		--profile=profiles/$(PROFILE) \
		--configfile $(CONFIG) \
		--report $(REPORTS)/$${DT}_report.html

run-file-server:
	$(CONDA_ACTIVATE) snakemake
	python -m  http.server --directory $(REPORTS) 8000

### extra

clean-meta:
	$(CONDA_ACTIVATE) snakemake
	$(SNAKEMAKE) \
	  --profile=profiles/$(PROFILE) \
	  --configfile $(CONFIG) \
	  --cleanup-metadata $(TARGET)

dag: CONFIG=configs/config.test.yml
dag:
	$(CONDA_ACTIVATE) snakemake
	$(SNAKEMAKE) \
	  --profile=profiles/$(PROFILE) \
	  --configfile $(CONFIG) \
	  --dag \
	  | dot -Tsvg > DAG.svg




################################################
### Local utils and CI
################################################

# OpusCleaner is a data cleaner for training corpus
# More details are in docs/cleaning.md
opuscleaner-ui:
	poetry install --only opuscleaner
	opuscleaner-server serve --host=0.0.0.0 --port=8000

# Utils to find corpus etc
install-utils:
	poetry install --only utils

# Black is a code formatter for Python files. Running this command will check that
# files are correctly formatted, but not fix them.
black:
	poetry install --only black
	@if poetry run black . --check --diff; then \
		echo "The python code formatting is correct."; \
	else \
	  echo ""; \
		echo "Python code formatting issues detected."; \
		echo "Run 'make black-fix' to fix them."; \
		echo ""; \
		exit 1; \
	fi

# Runs black, but also fixes the errors.
black-fix:
	poetry install --only black
	poetry run black .

# Runs ruff, a linter for python.
lint:
	poetry install --only lint
	poetry run ruff check .

# Runs ruff, but also fixes the errors.
lint-fix:
	poetry install --only lint
	poetry run ruff check . --fix

# Fix all automatically fixable errors. This is useful to run before pushing.
fix-all:
	make black-fix
	make lint-fix

# Validates Task Cluster task graph locally
validate-taskgraph:
	pip3 install -r taskcluster/requirements.txt && taskgraph full

# Downloads Marian training logs for a Taskcluster task group
download-logs:
	poetry install --only taskcluster
	python utils/tc_marian_logs.py --output=$$(pwd)/logs --task-group-id=$(LOGS_TASK_GROUP)

# Runs Tensorboard for Marian training logs in ./logs directory
# then go to http://localhost:6006
tensorboard:
	poetry install --only tensorboard
	marian-tensorboard --offline -f logs/*.log
