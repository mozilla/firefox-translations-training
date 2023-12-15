# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# This is a simple transform sequence that takes the `marian_args` referenced
# in a job, turns its key/value pairs into standard unix command line
# options, and makes them available to `task-context` substitutions as
# `marian_args`. For example:
# If the `marian_args` input resolves to: `{"beam-size": "12", "mini-batch-words": "2000"}`
# Then `marian_args` in `task-context` will be: `--beam-size 12 --mini-batch-words 2000`

from taskgraph.transforms.base import TransformSequence
from taskgraph.util.schema import Schema
from voluptuous import ALLOW_EXTRA, Required

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
        for name, value in deep_get(
            config.params, job.pop("marian-args")["from-parameters"]
        ).items():
            marian_args = marian_args + f" --{name} {value}"

        if "from-object" not in job["task-context"]:
            job["task-context"]["from-object"] = {}
        job["task-context"]["from-object"]["marian_args"] = marian_args

        yield job
