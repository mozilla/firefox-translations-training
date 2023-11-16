FROM $DOCKER_IMAGE_PARENT
LABEL maintainer="Mozilla Release Engineering <release+docker@mozilla.com>"

RUN apt-get update -qq \
    && apt-get install -y wget \
    && apt-get install -y pigz \
    && apt-get clean

VOLUME /builds/worker/checkouts
VOLUME /builds/worker/.cache
RUN chown worker:worker /builds/worker/.cache
