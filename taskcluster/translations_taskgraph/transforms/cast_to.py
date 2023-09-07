import copy

from taskgraph.transforms.base import TransformSequence
from taskgraph.util.schema import Schema
from voluptuous import ALLOW_EXTRA, Required, Optional, Any

from translations_taskgraph.util.dict_helpers import deep_get

SCHEMA = Schema(
    {
        Optional("cast-to"): {
            Optional("int"): [str],
        },
    },
    extra=ALLOW_EXTRA,
)

transforms = TransformSequence()
transforms.add_validate(SCHEMA)


@transforms.add
def cast(config, jobs):
    for job in jobs:
        casts = job.pop("cast-to", {})
        for field in casts.get("int", []):
            container, subfield = job, field
            while "." in subfield:
                f, subfield = subfield.split(".", 1)
                container = container[f]

            container[subfield] = int(container[subfield])

        yield job
