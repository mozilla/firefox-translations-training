import copy

from taskgraph.transforms.base import TransformSequence
from taskgraph.util.schema import Schema
from voluptuous import ALLOW_EXTRA, Required

from translations_taskgraph.util.dict_helpers import deep_get
from translations_taskgraph.util.substitution import substitute

SCHEMA = Schema(
    {
        Required("task-substitution"): {
            Required("from-parameters"): {str: str},
            Required("substitution-fields"): [str],
        },
    },
    extra=ALLOW_EXTRA,
)

transforms = TransformSequence()
transforms.add_validate(SCHEMA)


@transforms.add
def render_command(config, jobs):
    for job in jobs:
        sub_config = job.pop("task-substitution")
        subs = {}
        for var, path in sub_config["from-parameters"].items():
            subs[var] = deep_get(config.params, path)

        for field in sub_config["substitution-fields"]:
            container, subfield = job, field
            while "." in subfield:
                f, subfield = subfield.split(".", 1)
                container = container[f]

            container[subfield] = substitute(container[subfield], **subs)

        yield job

