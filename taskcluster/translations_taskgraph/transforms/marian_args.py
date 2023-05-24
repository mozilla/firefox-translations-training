import copy

from taskgraph.transforms.base import TransformSequence
from taskgraph.util.schema import Schema
from voluptuous import ALLOW_EXTRA, Required, Any

from translations_taskgraph.util.dict_helpers import deep_get

SCHEMA = Schema(
    {
        Required("marian-args"): {
            Required("from-parameters"): str,
        },
    },
    extra=ALLOW_EXTRA,
)

transforms = TransformSequence()
transforms.add_validate(SCHEMA)


@transforms.add
def render_command(config, jobs):
    for job in jobs:
        marian_args = ""
        for name, value in deep_get(config.params, job.pop("marian-args")["from-parameters"]).items():
            marian_args = marian_args + f" --{name} {value}"

        job.setdefault("run", {})
        job["run"].setdefault("command-context", {})
        job["run"]["command-context"]["marian_args"] = marian_args

        yield job
