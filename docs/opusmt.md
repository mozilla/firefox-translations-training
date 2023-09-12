# OPUS-MT integration
The integration with OPUS-MT is based on [GreenNLP fork](https://github.com/GreenNLP/firefox-translations-training).
This fork makes it possible to use OPUS-MT models as teacher and backward models in the _firefox-translations-training_ pipeline (FTT). Other additions are profiles for running jobs on CSC supercomputers (*puhti*, *lumi* and *mahti*) and code for monitoring the power usage of jobs.

# Workflow changes
- Added download rule for Tatoeba-Challenge data.
- Added download rule for OPUS-MT models (tested with Tatoeba-Challenge models, old models might need some changes)
- Added config parameters for specifying OPUS-MT models as teacher and/or backward model.
- Added subword segmentation and desegmentation rules.

# Subword segmentation issues
The biggest incompatibility with OPUS-MT models and FTT is in subword segmentation: default FTT trains models that use the in-built sentencepiece support in Marian, while OPUS-MT models expect data to be pre-segmented. To make it possible to use both the default FTT training and pre-built OPUS-MT models, segmentation and desegmentation steps have been added around marian-specific rules. This causes some clutter, but it's probably the best solution (instead of e.g. doing the segmentation/desegmentation inside the marian scripts), since it also makes it possible to easily implement other subword segmentation methods in the workflow. 


# Snakemake and conda on HPC
FTT is based on Snakemake, which has many benefits in terms of reproducibility and existing support. Among other things, Snakemake supports HPC environments and SLURM out of the box, which should make it ideal for CSC machines. However, Snakemake also makes heavy use of conda, which has been deprecated on CSC machines due to its unsuitability for HPC file systems (https://docs.csc.fi/computing/usage-policy/#conda-installations), and FTT specifically relies on several conda environments. Fortunately, Snakemake has a functionality for containerizing conda environments, so all the conda environments needed by FTT can be provided in an Apptainer container (Ftt.sif).

Containerization does not entirely solve the conda problem, since the Snakemake program itself requires conda to run. CSC provides a snakemake module, but problematically these modules are container-based, and since containers cannot be nested on CSC machines, it is not possible to use containerized conda environments with the CSC snakemake modules. This can be solved by installing Snakemake with pip (this is discouraged in the Snakemake documentation, but I have seen no problems so far).

# Non-containerized software
FTT uses software that is not included in the containerized conda environments, including several marian installations and other NLP tools. These are automatically built as part of the pipeline. The Ftt.sif container includes the prerequisites for the software components. It's also possible to provide paths to separately built software installations. 

# Getting started on CSC's puhti and mahti
1. Clone the repository.
2. Download the Ftt.sif container to the repository root.
3. Create a virtual Python environment for Snakemake (e.g. in the parent dir of the repository):
    1. The environment needs to be created with a non-containerized python, as otherwise Apptainer integration will not work. On puhti and mahti, the python executables in /usr/bin/ should work: `/usr/bin/python3.9 -m venv snakemake_env`.
    2. Activate the virtual environment: `source ./snakemake_env/bin/activate`.
    3. Install snakemake: `pip install snakemake`.
4. Install micromamba (e.g. in the parent dir of the repository): `curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba`
5. Return to the repository directory and update Git submodules: `make git-modules`
6. Create a _data_ directory (e.g. in the parent dir of the repository) and create a _tmp_ dir in it.
7. If the data directory is not located in the parent directory of the repository, edit _profiles/slurm-puhti/config.yaml_ or _profiles/slurm-mahti/config.yaml_ and change the bindings in the singularity-args section to point to your data directory, and also enter the _data_ directory path as the _root_ value of the _config_ section.
8. Edit profiles/slurm-puhti/config.cluster.yaml to change the CSC account to one you have access to. 
9. Load cuda modules: module load gcc/9.4.0 cuda cudnn
10. Run pipeline: `make run-hpc PROFILE="slurm-puhti"` or `make run PROFILE="slurm-mahti"`

# Getting started on CSC's lumi
1. Clone the repository.
2. Download the Ftt.sif container to the repository root.
3. Create a virtual Python environment for Snakemake (e.g. in the parent dir of the repository):
    1. The environment needs to be created with a non-containerized python, as otherwise Apptainer integration will not work. On lumi, use the _cray-python_ module (it is not containerized): `module load cray-python; python -m venv snakemake_env`.
    2. Activate the virtual environment: `source ./snakemake_env/bin/activate`.
    3. Install snakemake: `pip install snakemake`.
4. Install micromamba (e.g. in the parent dir of the repository): `curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba`
5. Return to the repository directory and update Git submodules: `make git-modules`
6. Create a _data_ directory (e.g. in the parent dir of the repository) and create a _tmp_ dir in it.
7. If the data directory is not located in the parent directory of the repository, edit profiles/slurm-lumi/config.yaml and change the bindings in the singularity-args section to point to your data directory, and also enter the _data_ directory path as the _root_ value of the _config_ section.
8. Edit profiles/slurm-puhti/config.cluster.yaml to change the CSC account to one you have access to. 
9. Load rocm module: module load rocm.
10. Copy the marian executables to _3rd_party/lumi-marian/build_ (compiling lumi-marian is currently hacky, so this workaround makes things easier).
11. Enter _export SINGULARITYENV_LD_LIBRARY_PATH=$LD_LIBRARY_PATH_ to make sure Marian can find all the libraries when it runs containerized.
12. Run pipeline: `make run-hpc PROFILE="slurm-puhti"`

# Testing
Since running the whole pipeline for a high-resource language pair will take a long time, there is a test config available for testing that everything works as it should. The test config is used by default, you can change into the full config by modifying the Makefile and changing config.opusmt-test.yml to config.opusmt.yml. You can also provide the config on the command line as the CONFIG parameter with make. Note that even the test config will take a long time if the training corpus is large (since translating the training data will take time). So to do a quick functionality check, pick a language pair with as little data as possible in Tatoeba-Challenge (while still having trained forward and backward models). The default epo-afr is good for quick checking (although note that bicleaner step will be skipped, as there are no bicleaner packs for those languages).

You can test the pipeline without running it by using make dry-run. If you want to build a specific file or rule, you can use the TARGET parameter with make. 
