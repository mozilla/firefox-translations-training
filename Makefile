#!make

.ONESHELL:
SHELL=/bin/bash

SHARED_ROOT=/data/rw/group-maml

CONDA_ACTIVATE=source $(SHARED_ROOT)/mambaforge/etc/profile.d/conda.sh ; conda activate ; conda activate
LOCAL_GPUS=8

all: install-conda, install-snakemake, activate, dry-run

install-conda:
	wget https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$$(uname)-$$(uname -m).sh
	bash Mambaforge-$$(uname)-$$(uname -m).sh -p $(SHARED_ROOT)/mambaforge

install-snakemake:
	git submodule update --init --recursive
	$(CONDA_ACTIVATE) base
	mamba create -c conda-forge -c bioconda -n snakemake snakemake
	conda install -c bioconda snakefmt

activate:
	$(CONDA_ACTIVATE) snakemake

dry-run:
	snakemake \
	  --use-conda \
	  --cores all \
	  -n

run-local: activate
	snakemake \
	  --use-conda --reason \
	  --cores all \
	  --resources gpu=$(LOCAL_GPUS)
	$(MAKE) report

report: activate
	REPORTS=$$(python -c "from config import reports_dir; print(reports_dir)"); \
	mkdir -p $$REPORTS && \
	snakemake --report $$REPORTS/report.html

run-snakepit: activate
	chmod +x profiles/snakepit/*
	snakemake \
	  --use-conda \
	  --cores all \
	  --profile=profiles/snakepit


run-slurm: activate
	chmod +x profiles/slurm/*
	snakemake \
	  --use-conda --reason --use-singularity \
	  --cores 16 \
	  --profile=profiles/slurm \
	  --singularity-args="--bind $(SHARED_ROOT):$(SHARED_ROOT) --nv"

dag:
	snakemake --dag | dot -Tpdf > DAG.pdf

lint:
	snakemake --lint

format:
	snakefmt --line-length 120 Snakefile

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


install-singularity: activate
	conda install singularity
	pip install spython
	apt-get -y install tzdata

containerize: activate
	snakemake --containerize > Dockerfile
	spython recipe Dockerfile &> Singularity.def

run-container: activate
	snakemake \
	  --use-conda --reason --use-singularity \
	  --cores all \
	  --resources gpu=$(LOCAL_GPUS) --singularity-args "--bind $(SHARED_ROOT):$(SHARED_ROOT) --nv"

build-container: activate
	singularity build Singularity.sif Singularity.def

pull-container: activate
	singularity pull Singularity.sif library://evgenypavlov/default/bergamot:sha256.269c037aeef3f050bb8aa67eae78307efa922207d6a78a553bf20fa969dce39f

run-file-server: activate
	python -m  http.server --directory $(SHARED_ROOT)/bergamot/reports 8000

tensorboard: activate
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