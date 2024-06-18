# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from taskgraph.transforms.base import TransformSequence
from taskgraph.util.schema import Schema
from voluptuous import ALLOW_EXTRA, Optional, Required

SCHEMA = Schema(
    {
        Required("fetches-from-upstreams"): {
            Required("attribute"): str,
            Optional("extra"): dict,
        },
    },
    extra=ALLOW_EXTRA,
)
transforms = TransformSequence()


@transforms.add
def fetches_from_upstream(config, jobs):
    for job in jobs:
        fetch_config = job.pop("fetches-from-upstreams")
        attribute = fetch_config["attribute"]
        extra = fetch_config.get("extra", {})

        artifacts_by_upstream = {}

        for task in sorted(config.kind_dependencies_tasks.values(), key=lambda t: t.label):
            if attribute not in task.attributes:
                continue

            artifacts_by_upstream[task.label] = task.attributes.get(attribute, [])

        job.setdefault("fetches", {})
        for label, artifacts in artifacts_by_upstream.items():
            label_fetches = []
            for artifact in artifacts:
                label_fetches.append(
                    {
                        "artifact": artifact,
                        **extra,
                    },
                )

            job["fetches"][label] = label_fetches

        yield job
