# nvidia-docker build . -t bergamot

FROM nvidia/cuda:11.2.0-runtime-ubuntu18.04

RUN apt-get update; exit 0 # For some reason, fails the first time, but is necessary
RUN apt-get update
RUN apt-get install git -y
RUN apt-get install nvidia-cuda-toolkit -y # Marian requires this toolkit

RUN git clone https://github.com/mozilla/firefox-translations-training.git
WORKDIR firefox-translations-training

RUN chmod +x ./pipeline/setup/install-deps.sh
RUN ./pipeline/setup/install-deps.sh

RUN make conda
RUN make snakemake
RUN make git-modules

RUN make dry-run
RUN make test # Downloads and compiles additional packages
