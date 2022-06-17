#!make

.ONESHELL:
SHELL=/bin/bash

### 1. change these settings or override with env variables
CONFIG=configs/config.prod.yml
CONDA_PATH=../mambaforge
SNAKEMAKE_OUTPUT_CACHE=../cache
PROFILE=local
# execution rule or path to rule output, default is all
TARGET=
REPORTS=../reports
# for tensorboard
MODELS=../models

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
	mamba create -c conda-forge -c bioconda -n snakemake snakemake==6.12.2 --yes
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
	  | dot -Tpdf > DAG.pdf

install-tensorboard:
	$(CONDA_ACTIVATE) base
	conda env create -f envs/tensorboard.yml

tensorboard:
	$(CONDA_ACTIVATE) tensorboard
	ls -d $(MODELS)/*/*/* > tb-monitored-jobs
	tensorboard --logdir=$(MODELS) --host=0.0.0.0 &
	python utils/tb_log_parser.py --prefix=