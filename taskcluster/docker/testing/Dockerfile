FROM $DOCKER_IMAGE_PARENT
LABEL maintainer="Mozilla Release Engineering <release+docker@mozilla.com>"

RUN pip install poetry

VOLUME /builds/worker/checkouts
# Poetry requires this folder.
VOLUME /builds/worker/.cache

RUN mkdir               /builds/worker/.cache && \
    chown worker:worker /builds/worker/.cache && \
    chmod a+rwX         /builds/worker/.cache
