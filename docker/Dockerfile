# A Docker image to run tests or experiment locally on a CPU machine
# It should be based on /taskcluster/docker/test/Dockerfile

ARG DOCKER_IMAGE_PARENT
FROM $DOCKER_IMAGE_PARENT

# Similar to /taskcluster/docker/toolchain/Dockerfile
RUN apt-get update -qq \
    # We need to install tzdata before all of the other packages. Otherwise it will show an interactive dialog that
    # we cannot navigate while building the Docker image.
    && apt-get install -y tzdata \
    && apt-get install -y wget \
                          curl \
                          zip \
                          build-essential \
                          gcc \
                          g++ \
                          make \
                          cmake \
                          libboost-dev \
                          libboost-all-dev \
                          zstd \
                          tar \
                          libxml2 \
                          libhunspell-dev \
                          bc \
                          libopenblas-dev \
                          openssl \
                          libssl-dev  \
         && apt-get clean

RUN mkdir /builds/worker/tools && \
    chown worker:worker /builds/worker/tools && \
    mkdir /builds/worker/tools/bin && \
    chown worker:worker /builds/worker/tools/bin

WORKDIR /builds/worker/tools

ADD pipeline/setup/* .

ENV BIN=/builds/worker/tools/bin

RUN git clone https://github.com/marian-nmt/extract-lex.git extract-lex
RUN ./compile-extract-lex.sh extract-lex/build $(nproc)

RUN git clone https://github.com/clab/fast_align.git fast_align
RUN ./compile-fast-align.sh fast_align/build $(nproc)

RUN git clone https://github.com/kpu/preprocess.git preprocess
RUN ./compile-preprocess.sh preprocess/build $(nproc)

RUN git clone https://github.com/marian-nmt/marian-dev.git marian-dev
# Use the same revision as in taskcluster/kinds/fetch/toolchains.yml
# it corresponds to v1.12.14 2d067afb 2024-02-16 11:44:13 -0500
RUN cd marian-dev && git checkout 2d067afb9ce5e3a0b6c32585706affc6e7295920
RUN ./compile-marian.sh marian-dev/build $(nproc) false

ENV MARIAN=/builds/worker/tools/marian-dev/build

# Work around poetry not finding `python`.
# https://github.com/python-poetry/poetry/issues/6371
RUN ln -s /bin/python3 /bin/python

# Install taskfile - https://taskfile.dev/
# Keep the version in sync with taskcluster/docker/test/Dockerfile.
RUN curl -sSLf "https://github.com/go-task/task/releases/download/v3.35.1/task_linux_amd64.tar.gz" \
    | tar -xz -C /usr/local/bin

# In some operating systems, the .git configuration will complain if the users
# do not match for the .git. Since this is a local environment, we don't worry about
# permissions escalation exploits that may be an issue in a production docker container.
RUN git config --global --add safe.directory /builds/worker/checkouts
