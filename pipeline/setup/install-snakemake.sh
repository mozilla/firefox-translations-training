#!/bin/bash

wget https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$(uname)-$(uname -m).sh
bash Mambaforge-$(uname)-$(uname -m).sh

conda activate base
mamba create -c conda-forge -c bioconda -n snakemake snakemake
conda activate snakemake