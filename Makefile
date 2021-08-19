.ONESHELL:
SHELL=/bin/bash
CONDA_ACTIVATE=source $$(conda info --base)/etc/profile.d/conda.sh ; conda activate ; conda activate
SHARED_ROOT=/data/rw/group-maml


all: dry-run

install-conda:
	wget https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$(uname)-$(uname -m).sh
	bash Mambaforge-$(uname)-$(uname -m).sh -p $(SHARED_ROOT)/mambaforge

install: install-conda
	$(CONDA_ACTIVATE) base
	mamba create -c conda-forge -c bioconda -n snakemake snakemake
	activate

activate:
	$(CONDA_ACTIVATE) snakemake

dry-run:
	snakemake \
	  --use-conda \
	  --cores all \
	  -n

run-local:
	snakemake \
	  --use-conda \
	  --cores all

run-cluster:
	chmod +x profiles/snakepit/*
	snakemake \
	  --use-conda \
	  --cores all \
	  --profile=profiles/snakepit

dag:
	snakemake --dag | dot -Tpdf > dag.pdf

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

	unset http_proxy
	echo "http://10.2.224.243" > /root/.pitconnect.txt

	pit status