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
	poetry install --only opuscleaner --no-root
	opuscleaner-server serve --host=0.0.0.0 --port=8000

# Utils to find corpus etc
install-utils:
	poetry install --only utils --no-root

# Black is a code formatter for Python files. Running this command will check that
# files are correctly formatted, but not fix them.
black:
	poetry install --only black --no-root
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
	poetry install --only black --no-root
	poetry run black .

# Runs ruff, a linter for python.
lint:
	poetry install --only lint --no-root
	poetry run ruff --version
	poetry run ruff check .

# Runs ruff, but also fixes the errors.
lint-fix:
	poetry install --only lint --no-root
	poetry run ruff check . --fix

# Fix all automatically fixable errors. This is useful to run before pushing.
fix-all:
	make black-fix
	make lint-fix

# Run unit tests
run-tests:
	poetry install --only tests --only utils --no-root
	PYTHONPATH=$$(pwd) poetry run pytest tests -vv

# Validates Taskcluster task graph locally
validate-taskgraph:
	pip3 install -r taskcluster/requirements.txt && taskgraph full

# Generates diffs of the full taskgraph against $BASE_REV. Any parameters that were
# different between the current code and $BASE_REV will have their diffs logged to $OUTPUT_DIR.
diff-taskgraph:
ifndef OUTPUT_DIR
	$(error OUTPUT_DIR must be defined)
endif
ifndef BASE_REV
	$(error BASE_REV must be defined)
endif
	pip3 install -r taskcluster/requirements.txt
	taskgraph full -p "taskcluster/test/params" -o "$(OUTPUT_DIR)" --diff "$(BASE_REV)" -J

# Downloads Marian training logs for a Taskcluster task group
download-logs:
	mkdir -p data/taskcluster-logs
	poetry install --only taskcluster --no-root
	poetry run python utils/taskcluster_downloader.py \
		--output=data/taskcluster-logs/$(LOGS_TASK_GROUP) \
		--mode=logs \
		--task-group-id=$(LOGS_TASK_GROUP)

# Downloads evaluation results from Taskcluster task group to a CSV file
# This includes BLEU and chrF metrics for each dataset and trained model
download-evals:
	mkdir -p data/taskcluster-logs
	poetry install --only taskcluster --no-root
	poetry run python utils/taskcluster_downloader.py \
		--output=data/taskcluster-evals/$(LOGS_TASK_GROUP) \
		--mode=evals \
		--task-group-id=$(LOGS_TASK_GROUP)


# Runs Tensorboard for Marian training logs in ./logs directory
# then go to http://localhost:6006
tensorboard:
	mkdir -p data/tensorboard-logs
	poetry install --only tensorboard --no-root
	poetry run marian-tensorboard \
		--offline \
		--log-file data/taskcluster-logs/**/*.log \
		--work-dir data/tensorboard-logs

# Run the GitHub pages Jekyll theme locally.
# TODO - This command would be better to be run in a docker container, as the
# requirement for rbenv is a little brittle.
serve-docs:
	echo "This command requires"
	echo "  rbenv: https://github.com/rbenv/rbenv"
	echo "  rbenv install 3.2.2"

	cd docs                         \
	&& eval "$$(rbenv init - make)" \
	&& rbenv local 3.2.2            \
	&& rbenv shell                  \
	&& bundle install               \
	&& bundle exec jekyll serve

preflight-check:
	poetry install --only utils --no-root
	poetry run python -W ignore utils/preflight_check.py
