ARG DOCKER_IMAGE_PARENT
FROM $DOCKER_IMAGE_PARENT
LABEL maintainer="Mozilla Release Engineering <release+docker@mozilla.com>"

RUN apt-get update -qq \
    && apt-get install -y \
      wget \
      parallel \
      pigz \
      unzip \
      zstd \
    && apt-get clean


RUN pip install poetry

VOLUME /builds/worker/checkouts
VOLUME /builds/worker/.cache

