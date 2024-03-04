#!make

.ONESHELL:
SHELL=/bin/bash

# task group id for downloading evals and logs
LOGS_TASK_GROUP?=

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

# Download binaries from Taskcluster to run tests
# See https://firefox-ci-tc.services.mozilla.com/tasks/index/translations.cache.level-1.toolchains.v3.fast-align/latest
download-bin:
	BIN=bin bash utils/download-bin.sh

# Run unit tests
# Some tests work only on Linux, use Docker if running locally on other OS
run-tests:
	poetry install --only tests --only utils --no-root
	PYTHONPATH=$$(pwd) poetry run pytest -vv

# Run unit tests locally under Docker
# !!! IMPORTANT !!! on Apple Silicon run without poetry shell for the first time
# as it can change `uname -m` output to x86_64 if it runs under Rosetta
run-tests-docker:
  	# build docker images for apple silicon
	if [ $$(uname -m) == 'arm64' ]; then \
		echo "setting arm64 platform"; \
	  	export DOCKER_DEFAULT_PLATFORM=linux/amd64; \
	fi && \
	docker build \
		--file taskcluster/docker/base/Dockerfile \
		--tag ftt-base . && \
	docker build \
		--build-arg DOCKER_IMAGE_PARENT=ftt-base \
		--file taskcluster/docker/test/Dockerfile \
		--tag ftt-test . && \
	docker run -it --rm -v $$(pwd):/builds/worker/checkouts -w /builds/worker/checkouts ftt-test make run-tests

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
	# --output-file takes a base file name which has specific parameter file names appended to it for each
	# diff done.
	taskgraph full -p "taskcluster/test/params" --output-file "$(OUTPUT_DIR)/diff" --diff "$(BASE_REV)" -J

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
