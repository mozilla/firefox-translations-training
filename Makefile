#!make

.ONESHELL:
SHELL=/bin/bash

### 1. change these settings
SHARED_ROOT=/data/rw/group-maml
CUDA_DIR=/usr/local/cuda
CUDNN_DIR=/usr/lib/x86_64-linux-gnu
NUM_GPUS=8
# (optional) override available GPU ids, example GPUS=0 2 5 6
GPUS=
WORKSPACE=12000
CLUSTER_CORES=16
CONFIG=configs/config.prod.yml
CONDA_PATH=$(SHARED_ROOT)/mambaforge
SNAKEMAKE_OUTPUT_CACHE=$(SHARED_ROOT)/cache
SLURM_PROFILE=slurm-moz
# for CSD3 cluster
# MARIAN_CMAKE=-DBUILD_ARCH=core-avx2
MARIAN_CMAKE=
TARGET=

###

CONDA_ACTIVATE=source $(CONDA_PATH)/etc/profile.d/conda.sh ; conda activate ; conda activate
SNAKEMAKE=export SNAKEMAKE_OUTPUT_CACHE=$(SNAKEMAKE_OUTPUT_CACHE);  snakemake
CONFIG_OPTIONS=root="$(SHARED_ROOT)" cuda="$(CUDA_DIR)" cudnn=/cudnn workspace=$(WORKSPACE) numgpus=$(NUM_GPUS) $(if $(MARIAN_CMAKE),mariancmake="$(MARIAN_CMAKE)",) $(if $(GPUS),gpus="$(GPUS)",)

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


### 3. run

# if you need to activate conda environment for direct snakemake commands, use
# . $(CONDA_PATH)/etc/profile.d/conda.sh && conda activate snakemake

dry-run:
	$(CONDA_ACTIVATE) snakemake
	$(SNAKEMAKE) \
	  --use-conda \
	  --cores all \
	  --cache \
	  --verbose \
	  --reason \
	  --configfile $(CONFIG) \
	  --config $(CONFIG_OPTIONS) deps=true  \
	  -n \
	  $(TARGET)

test-dry-run: CONFIG=configs/config.test.yml
test-dry-run: dry-run

run-local:
	echo "Running with config $(CONFIG)"
	$(CONDA_ACTIVATE) snakemake
	$(SNAKEMAKE) \
	  --use-conda \
	  --resources gpu=$(NUM_GPUS) \
	  --configfile $(CONFIG) \
	  --config $(CONFIG_OPTIONS) deps=true \
	  --cores all \
	  --cache \
	  --reason \
	  $(TARGET)

test: CONFIG=configs/config.test.yml
test: run-local

run-local-container:
	$(CONDA_ACTIVATE) snakemake
	module load singularity
	$(SNAKEMAKE) \
	  --use-conda \
	  --use-singularity \
	  --reason \
	  --cores all \
	  --cache \
	  --resources gpu=$(NUM_GPUS) \
	  --configfile $(CONFIG) \
	  --config $(CONFIG_OPTIONS) \
	  --singularity-args="--bind $(SHARED_ROOT),$(CUDA_DIR),$(CUDNN_DIR):/cudnn --nv" \
	  $(TARGET)

run-slurm:
	$(CONDA_ACTIVATE) snakemake
	chmod +x profiles/$(SLURM_PROFILE)/*
	$(SNAKEMAKE) \
	  --use-conda \
	  --reason \
	  --cores $(CLUSTER_CORES) \
	  --cache \
	  --configfile $(CONFIG) \
	  --config $(CONFIG_OPTIONS) \
	  --profile=profiles/$(SLURM_PROFILE) \
	  $(TARGET)

run-slurm-container:
	$(CONDA_ACTIVATE) snakemake
	chmod +x profiles/$(SLURM_PROFILE)/*
#	module load singularity
	$(SNAKEMAKE) \
	  --use-conda \
	  --use-singularity \
	  --reason \
	  --cores $(CLUSTER_CORES) \
	  --cache \
	  --configfile $(CONFIG) \
	  --config $(CONFIG_OPTIONS) \
	  --profile=profiles/$(SLURM_PROFILE) \
	  --singularity-args="--bind $(SHARED_ROOT),$(CUDA_DIR),$(CUDNN_DIR):/cudnn,/tmp --nv --containall" \
	  $(TARGET)
# if CPU nodes don't have access to cuda dirs, use
# export CUDA_DIR=$(CUDA_DIR); $(SNAKEMAKE) \
# --singularity-args="--bind $(SHARED_ROOT),/tmp --nv --containall"


### 4. create a report

report:
	$(CONDA_ACTIVATE) snakemake
	REPORTS=$(SHARED_ROOT)/reports DT=$$(date '+%Y-%m-%d_%H-%M'); \
	mkdir -p $$REPORTS && \
	snakemake \
		--report $${REPORTS}/$${DT}_report.html \
		--configfile $(CONFIG) \
		--config $(CONFIG_OPTIONS)

run-file-server:
	$(CONDA_ACTIVATE) snakemake
	python -m  http.server --directory $(SHARED_ROOT)/reports 8000

### extra

clean-meta:
	$(CONDA_ACTIVATE) snakemake
	$(SNAKEMAKE) \
	  --use-conda \
	  --cores all \
	  --configfile $(CONFIG) \
	  --config $(CONFIG_OPTIONS) \
	  --cleanup-metadata $(TARGET)

dag: CONFIG=configs/config.test.yml
dag:
	snakemake \
	  --dag \
	  --configfile $(CONFIG) \
	  --config $(CONFIG_OPTIONS) \
	  | dot -Tpdf > DAG.pdf

install-tensorboard:
	$(CONDA_ACTIVATE) base
	conda env create -f envs/tensorboard.yml

tensorboard:
	$(CONDA_ACTIVATE) tensorboard
	ls -d $(SHARED_ROOT)/models/*/*/* > tb-monitored-jobs; \
	tensorboard --logdir=$$MODELS --host=0.0.0.0 &; \
	python utils/tb_log_parser.py --prefix=