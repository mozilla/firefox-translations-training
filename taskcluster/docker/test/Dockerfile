ARG DOCKER_IMAGE_PARENT
FROM $DOCKER_IMAGE_PARENT
LABEL maintainer="Mozilla Release Engineering <release+docker@mozilla.com>"

RUN apt-get update -qq \
    && apt-get install -y \
      curl \
      parallel \
      pigz \
      unzip \
      zstd \
      bc \
      libhunspell-1.7-0 \
      libboost-program-options1.74.0 \
      libboost-filesystem1.74.0 \
      libboost-iostreams1.74.0 \
      python3.10-venv \
    && apt-get clean


RUN pip install poetry
# we do not run poetry install here because the tracking package is installed from code

# Install taskfile - https://taskfile.dev/
# Keep the version in sync with docker/Dockerfile.
RUN curl -sSLf "https://github.com/go-task/task/releases/download/v3.35.1/task_linux_amd64.tar.gz" \
    | tar -xz -C /usr/local/bin

VOLUME /builds/worker/checkouts
VOLUME /builds/worker/.cache

# Install the test venvs
RUN mkdir -p /builds/worker/checkouts/data/task-venvs
RUN mkdir -p /builds/worker/checkouts/requirements

WORKDIR /builds/worker/checkouts
ADD tests/fixtures/install_venvs.py .

# Doing the installs as individual steps makes it easier to cache each layer, and deal with
# requirements that fail to load.

ADD pipeline/quantize/requirements/quantize.txt      requirements
RUN python3 install_venvs.py --output /builds/worker/checkouts/data --requirements requirements/quantize.txt
ADD pipeline/translate/requirements/splitter.txt     requirements
RUN python3 install_venvs.py --output /builds/worker/checkouts/data --requirements requirements/splitter.txt
ADD pipeline/clean/requirements/merge-mono.txt       requirements
RUN python3 install_venvs.py --output /builds/worker/checkouts/data --requirements requirements/merge-mono.txt
ADD pipeline/clean/requirements/clean.txt            requirements
RUN python3 install_venvs.py --output /builds/worker/checkouts/data --requirements requirements/clean.txt
ADD pipeline/train/requirements/train.txt            requirements
RUN python3 install_venvs.py --output /builds/worker/checkouts/data --requirements requirements/train.txt
ADD pipeline/eval/requirements/eval.txt              requirements
RUN python3 install_venvs.py --output /builds/worker/checkouts/data --requirements requirements/eval.txt
ADD pipeline/alignments/requirements/alignments.txt  requirements
RUN python3 install_venvs.py --output /builds/worker/checkouts/data --requirements requirements/alignments.txt
ADD pipeline/data/requirements/analyze.txt           requirements
RUN python3 install_venvs.py --output /builds/worker/checkouts/data --requirements requirements/analyze.txt
ADD pipeline/data/requirements/data.txt              requirements
RUN python3 install_venvs.py --output /builds/worker/checkouts/data --requirements requirements/data.txt

# This requirements file will only install if specific packages are built first. In Taskcluster
# this is done through fetches. Skip this install for now.
#
#    ADD pipeline/bicleaner/requirements/bicleaner-ai.txt requirements
#    RUN python3 install_venvs.py --output /builds/worker/checkouts/data --requirements requirements/bicleaner-ai.txt

# Clean up.
RUN rm -rf /builds/worker/checkouts/requirements
RUN rm install_venvs.py
