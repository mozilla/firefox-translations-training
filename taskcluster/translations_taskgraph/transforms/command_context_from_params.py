import copy

from taskgraph.transforms.base import TransformSequence
from taskgraph.util.schema import Schema
from voluptuous import ALLOW_EXTRA, Required, Any, Optional

from translations_taskgraph.util.dict_helpers import deep_get

SCHEMA = Schema(
    {
        Required("run"): {
            Required("command-context"): {
                Optional("from-parameters"): {
                    str: Any([str], str),
                },
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

        for param, path in job["run"]["command-context"].get("from-parameters", {}).items():
            if isinstance(path, str):
                value = deep_get(config.params, path)
                subjob["run"]["command-context"][param] = value
            else:
                for choice in path:
                    value = deep_get(config.params, choice)
                    if value is not None:
                        subjob["run"]["command-context"][param] = value
                        break

        yield subjob
