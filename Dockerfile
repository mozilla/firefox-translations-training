FROM ubuntu:18.04
LABEL io.github.snakemake.containerized="true"
LABEL io.github.snakemake.conda_env_hash="0cb76977b53fce1e0c610eb57e9eba65fe6cba8965b388bf0ce70c71fbf4a1e2"

RUN apt-get update
RUN apt-get install -y pigz htop wget unzip parallel
RUN apt-get install -y build-essential libboost-system-dev libprotobuf10 \
  protobuf-compiler libprotobuf-dev openssl libssl-dev libgoogle-perftools-dev
RUN apt-get install -y libgoogle-perftools-dev libsparsehash-dev libboost-all-dev

RUN wget https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$(uname)-$(uname -m).sh

ENV CONDA_DIR=/opt/conda
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV PATH=${CONDA_DIR}/bin:${PATH}

RUN bash Mambaforge-$(uname)-$(uname -m).sh -b -p ${CONDA_DIR}
RUN . ${CONDA_DIR}/etc/profile.d/conda.sh && conda activate base

# Step 1: Retrieve conda environments

# Conda environment:
#   source: envs/base.yml
#   prefix: /conda-envs/d0d654bc91b4ab9921d1b5e4d4b0ad2f
#   name: bergamot-training
#   channels:
#     - conda-forge
#     - defaults
#   dependencies:
#     - python=3.9
#     - cmake=3.21.1
#     - mkl=2021.3.0
#     - git=2.32.0
#     - pip=21.2.2
#     - pip:
#       - sacrebleu==1.5.1
#       - mtdata==0.2.9
#       - fasttext==0.9.2
#       - tensorboard==2.5.0
#       - tensorboardX==2.2
#       - click==8.0.1
#       - toolz==0.11.1
RUN mkdir -p /conda-envs/d0d654bc91b4ab9921d1b5e4d4b0ad2f
COPY envs/base.yml /conda-envs/d0d654bc91b4ab9921d1b5e4d4b0ad2f/environment.yaml

# Conda environment:
#   source: envs/bicleaner.yml
#   prefix: /conda-envs/a953cb928c2efb3191bbb90e0f26b225
#   name: bicleaner
#   channels:
#     - conda-forge
#     - defaults
#   dependencies:
#     - python=3.7
#     - pip==21.2.2
#     - scipy==1.4.1
#     - scikit-learn==0.22.1
#     - fasttext==0.9.2
#     - numpy>=1.18.1
#     - pip:
#       - bicleaner==0.14
RUN mkdir -p /conda-envs/a953cb928c2efb3191bbb90e0f26b225
COPY envs/bicleaner.yml /conda-envs/a953cb928c2efb3191bbb90e0f26b225/environment.yaml

# Step 2: Generate conda environments

RUN mamba env create --prefix /conda-envs/d0d654bc91b4ab9921d1b5e4d4b0ad2f --file /conda-envs/d0d654bc91b4ab9921d1b5e4d4b0ad2f/environment.yaml && \
    mamba env create --prefix /conda-envs/a953cb928c2efb3191bbb90e0f26b225 --file /conda-envs/a953cb928c2efb3191bbb90e0f26b225/environment.yaml && \
    mamba clean --all -y
