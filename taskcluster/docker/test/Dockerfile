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
    && apt-get clean


RUN pip install poetry
# we do not run poetry install here because the tracking package is installed from code

VOLUME /builds/worker/checkouts
VOLUME /builds/worker/.cache

