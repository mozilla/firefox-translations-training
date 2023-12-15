# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# This transform has a very simple job: cast fields in a task definition from
# one type to another. The only reason it exists is because we have some fields
# that `task_context` fills in as a string, but that other transforms or code
# requires to be an int.

from taskgraph.transforms.base import TransformSequence
from taskgraph.util.schema import Schema
from voluptuous import ALLOW_EXTRA, Optional


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
