import copy

from taskgraph.transforms.base import TransformSequence
from taskgraph.util.schema import Schema
from voluptuous import ALLOW_EXTRA, Required

SCHEMA = Schema(
    {
        Required("run"): {
            Required("command-context"): {
                Required("from-parameters"): [str],
            },
        },
    },
    extra=ALLOW_EXTRA,
)

transforms = TransformSequence()
transforms.add_validate(SCHEMA)


@transforms.add
def render_command(config, jobs):
    for job in jobs:
        subjob = copy.deepcopy(job)

        for param in job["run"]["command-context"]["from-parameters"]:
            subjob["run"]["command-context"][param] = config.params[param]

        yield subjob
