.ONESHELL:
SHELL=/bin/bash
CONDA_ACTIVATE=source $$(conda info --base)/etc/profile.d/conda.sh ; conda activate ; conda activate

all: dry-run

install-conda:
	wget https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$(uname)-$(uname -m).sh
	bash Mambaforge-$(uname)-$(uname -m).sh

install: install-conda
	$(CONDA_ACTIVATE) base
	mamba create -c conda-forge -c bioconda -n snakemake snakemake
	activate

activate:
	$(CONDA_ACTIVATE) snakemake

dry-run: activate
	snakemake \
	  --use-conda \
	  --cores all \
	  -n

run-local: activate
	snakemake \
	  --use-conda \
	  --cores all

run-cluster: activate
	snakemake \
	  --use-conda \
	  --cores all \
	  --profile=profiles/snakepit

dag: activate
	snakemake --dag | dot -Tpdf > dag.pdf

install-monitor:
	conda create --name panoptes
	conda install -c panoptes-organization panoptes-ui

run-monitor:
	$(CONDA_ACTIVATE) panoptes
	panoptes

run-with-monitor: activate
	snakemake \
	  --use-conda \
	  --cores all \
	  --wms-monitor http://127.0.0.1:5000