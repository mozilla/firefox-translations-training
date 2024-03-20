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
RUN ./compile-marian.sh marian-dev/build $(nproc) false

ENV MARIAN=/builds/worker/tools/marian-dev/build

# Work around poetry not finding `python`.
# https://github.com/python-poetry/poetry/issues/6371
RUN ln -s /bin/python3 /bin/python
