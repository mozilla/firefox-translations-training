#!make

.ONESHELL:
SHELL=/bin/bash

### 1. change these settings or override with env variables
CONFIG=configs/config.opusmt-multimodel-test.yml
CONDA_PATH=../mambaforge
SNAKEMAKE_OUTPUT_CACHE=../cache
#PROFILE=local
# execution rule or path to rule output, default is all
TARGET=
EXTRA=
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
	mamba create -c conda-forge -c bioconda -n snakemake snakemake==7.19.1 tabulate==0.8.10 --yes
	mkdir -p "$(SNAKEMAKE_OUTPUT_CACHE)"


containerize:
	$(CONDA_ACTIVATE) snakemake
	$(SNAKEMAKE) \
	  --profile=profiles/$(PROFILE) \
	  --configfile $(CONFIG) \
	  --containerize > Dockerfile
	spython recipe Dockerfile Ftt.def
	sed -i "s|%files|%files\npipeline/setup/install-deps.sh install-deps.sh|" Ftt.def
	sed -i 's#%post#%post\ncat /etc/apt/sources.list | sed "s/archive.ubuntu.com/mirrors.nic.funet.fi/g" > temp \&\& mv temp /etc/apt/sources.list \
		\napt-get update \&\& apt-get -y install gcc g++ \
		\nexport DEBIAN_FRONTEND=noninteractive \
		\nbash install-deps.sh#' Ftt.def
	apptainer build Ftt.sif Ftt.def

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
	  $(TARGET) \
	  $(EXTRA) \

dry-run-hpc:
	echo "Dry run with config $(CONFIG) and profile $(PROFILE)"
	$(SNAKEMAKE) \
	  --profile=profiles/$(PROFILE) \
	  --configfile $(CONFIG) \
	  -n \
	  --conda-base-path=../bin \
	  $(TARGET) \
	  $(EXTRA)

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
	  $(TARGET) \
	  $(EXTRA)

run-hpc:
	echo "Running with config $(CONFIG) and profile $(PROFILE)"
	chmod +x profiles/$(PROFILE)/*
	$(SNAKEMAKE) \
	  --profile=profiles/$(PROFILE) \
	  --configfile $(CONFIG) \
	  --conda-base-path=../bin \
	  $(TARGET) \
	  $(EXTRA)
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
