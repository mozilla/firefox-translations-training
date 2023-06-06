# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import copy

from taskgraph.transforms.base import TransformSequence
from taskgraph.util.schema import Schema, optionally_keyed_by, resolve_keyed_by
from voluptuous import ALLOW_EXTRA, Required, Optional

from translations_taskgraph.util.dict_helpers import deep_get
from translations_taskgraph.util.substitution import substitute

CHUNK_SCHEMA = Schema(
    {
        # Optional, so it can be used for a subset of jobs in a kind
        Optional("chunk-config"): {
            Required("total-chunks"): {
                Required("from-parameters"): str,
            },
            Optional("substitution-fields"): [str],
        }
    },
    extra=ALLOW_EXTRA,
)

chunk = TransformSequence()
chunk.add_validate(CHUNK_SCHEMA)


UNCHUNK_SCHEMA = Schema(
    {
        Optional("chunk-config"): {
            Required("total-chunks"): {
                Required("from-parameters"): str,
            },
            Optional("per-upstream-fields"): object,
        }
    },
    extra=ALLOW_EXTRA,
)

unchunk = TransformSequence()
unchunk.add_validate(UNCHUNK_SCHEMA)


@chunk.add
def chunk_jobs(config, jobs):
    for job in jobs:
        chunk_config = job.pop("chunk-config", None)
        if not chunk_config:
            yield job
            continue

        total_chunks = deep_get(config.params, chunk_config["total-chunks"]["from-parameters"])
        
        for this_chunk in range(1, total_chunks + 1):
            subjob = copy.deepcopy(job)
            
            subs = {
                "this_chunk": this_chunk,
                "total_chunks": total_chunks,
            }

            for field in chunk_config["substitution-fields"]:
                container, subfield = subjob, field
                while "." in subfield:
                    f, subfield = subfield.split(".", 1)
                    container = container[f]

                container[subfield] = substitute(container[subfield], **subs)

            yield subjob


@unchunk.add
def do_unchunking(config, jobs):
    for job in jobs:
        chunk_config = job.pop("chunk-config", None)
        if not chunk_config:
            yield job
            continue

        total_chunks = deep_get(config.params, chunk_config["total-chunks"]["from-parameters"])
        
        for this_chunk in range(1, total_chunks + 1):
            subs = {
                "this_chunk": this_chunk,
                "total_chunks": total_chunks,
            }

            for field, value in chunk_config.get("per-upstream-fields", {}).items():
                if field not in job:
                    field[job] = {}

                job[field].update(substitute(copy.deepcopy(value), **subs))

        yield job
