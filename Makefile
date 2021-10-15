#!make

.ONESHELL:
SHELL=/bin/bash

### 1. change these settings
SHARED_ROOT=/data/rw/group-maml
CUDA_DIR=/usr/local/cuda
GPUS=8
WORKSPACE=12000
CLUSTER_CORES=16
CONFIG=configs/config.prod.yml
CONDA_PATH=$(SHARED_ROOT)/mambaforge
###

CONDA_ACTIVATE=source $(CONDA_PATH)/etc/profile.d/conda.sh ; conda activate ; conda activate

### 2. setup

install-git-modules:
	git submodule update --init --recursive

install-conda:
	wget https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$$(uname)-$$(uname -m).sh
	bash Mambaforge-$$(uname)-$$(uname -m).sh -b -p $(CONDA_PATH)

install-snakemake:
	$(CONDA_ACTIVATE) base
	mamba create -c conda-forge -c bioconda -n snakemake snakemake==6.9.1

# build container image for cluster and run-local modes (preferred)
build-container:
	sudo singularity build Singularity.sif Singularity.def

# or pull container image from a registry if there is no sudo
pull-container:
	singularity pull Singularity.sif library://evgenypavlov/default/bergamot2:latest


### 3. run

# conda init and restart shell
# or
# . $(CONDA_PATH)/etc/profile.d/conda.sh && conda activate
#
# conda activate snakemake

dry-run:
	snakemake \
	  --use-conda \
	  --cores all \
	  --configfile $(CONFIG) \
	  --config root="$(SHARED_ROOT)" cuda="$(CUDA_DIR)" gpus=$(GPUS) workspace=$(WORKSPACE) deps=true  \
	  -n

run-local-no-container:
	$(CONDA_ACTIVATE) snakemake
	snakemake \
	  --use-conda \
	  --reason \
	  --cores all \
	  --resources gpu=$(GPUS) \
	  --configfile $(CONFIG) \
	  --config root="$(SHARED_ROOT)" cuda="$(CUDA_DIR)" gpus=$(GPUS) workspace=$(WORKSPACE) deps=true

run-local:
	$(CONDA_ACTIVATE) snakemake
	module load singularity
	snakemake \
	  --use-conda \
	  --use-singularity \
	  --reason \
	  --cores all \
	  --resources gpu=$(GPUS) \
	  --configfile $(CONFIG) \
	  --config root="$(SHARED_ROOT)" cuda="$(CUDA_DIR)" gpus=$(GPUS) workspace=$(WORKSPACE) \
	  --singularity-args="--bind $(SHARED_ROOT),$(CUDA_DIR) --nv"

run-slurm:
	$(CONDA_ACTIVATE) snakemake
	chmod +x profiles/slurm/*
	export CUDA_DIR=$(CUDA_DIR)
	module load singularity
	snakemake \
	  --use-conda \
	  --use-singularity \
	  --reason \
	  --verbose \
	  --cores $(CLUSTER_CORES) \
	  --configfile $(CONFIG) \
	  --config root="$(SHARED_ROOT)" cuda="$(CUDA_DIR)" gpus=$(GPUS) workspace=$(WORKSPACE) \
	  --profile=profiles/slurm \
	  --singularity-args="--bind $(SHARED_ROOT) --nv"

# to not mount use bash profile if it breaks things
#	  --singularity-args="--bind $(SHARED_ROOT),/tmp --nv --containall"


### extra

report:
	REPORTS=$$(python -c "from config import reports_dir; print(reports_dir)"); \
	mkdir -p $$REPORTS && \
	snakemake --report $$REPORTS/report.html

dag:
	snakemake --dag | dot -Tpdf > DAG.pdf

lint:
	snakemake --lint

install-monitor:
	conda create --name panoptes
	conda install -c panoptes-organization panoptes-ui

run-monitor:
	$(CONDA_ACTIVATE) panoptes
	panoptes

run-with-monitor:
	snakemake \
	  --use-conda \
	  --cores all \
	  --wms-monitor http://127.0.0.1:5000

containerize:
	pip install spython
	snakemake --containerize > Dockerfile
	spython recipe Dockerfile &> Singularity.def

run-file-server:
	python -m  http.server --directory $(SHARED_ROOT)/bergamot/reports 8000

tensorboard:
	MODELS=$$(python -c "from config import models_dir; print(models_dir)"); \
	ls -d $$MODELS/*/*/* > tb-monitored-jobs; \
	tensorboard --logdir=$$MODELS --host=0.0.0.0 &; \
	python utils/tb_log_parser.py --prefix=

install-snakepit-scheduler:
	mkdir -p $(SHARED_ROOT)/snakepit
	cd $(SHARED_ROOT)/snakepit

	curl -sL https://deb.nodesource.com/setup_12.x | sudo -E bash -
	sudo apt install nodejs

	if [ ! -e snakepit-client ]; then
	  git clone https://github.com/mozilla/snakepit-client.git
	fi
	cd snakepit-client
	npm install
	sudo npm link

	echo "http://10.2.224.243" > /root/.pitconnect.txt

	pit status


run-snakepit:
	chmod +x profiles/snakepit/*
	snakemake \
	  --use-conda \
	  --cores all \
	  --profile=profiles/snakepit
